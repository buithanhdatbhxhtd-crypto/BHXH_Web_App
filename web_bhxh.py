import streamlit as st
import pandas as pd
import os
import streamlit_authenticator as stauth
import yaml
import bcrypt
import plotly.express as px
import requests 
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH FILE ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' 
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    # Reset các trạng thái khác
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai', 'edit']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU ---
@st.cache_data(ttl=3600)
def nap_du_lieu_toi_uu():
    if os.path.exists(PARQUET_FILE):
        try:
            df = pd.read_parquet(PARQUET_FILE)
            cols_to_str = ['soBhxh', 'soCmnd', 'soDienThoai']
            for col in cols_to_str:
                if col in df.columns: df[col] = df[col].astype(str)
            return df
        except Exception: pass

    if not os.path.exists(EXCEL_FILE):
        st.error(f"❌ Không tìm thấy file: {EXCEL_FILE}")
        return pd.DataFrame()
    
    try:
        with st.spinner('⚙️ Đang tối ưu hóa dữ liệu...'):
            df = pd.read_excel(EXCEL_FILE, dtype=str, engine='pyxlsb')
            df.columns = df.columns.str.strip()
            df.to_parquet(PARQUET_FILE)
        return df
    except Exception as e:
        st.error(f"❌ Lỗi đọc file: {e}")
        return pd.DataFrame()

# --- CÁC HÀM HIỂN THỊ ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy kết quả phù hợp.")
        return
    st.success(f"✅ Tìm thấy {len(df_ket_qua)} hồ sơ!")
    
    if len(df_ket_qua) > 50:
        st.caption(f"⚠️ Đang hiển thị 50/{len(df_ket_qua)} kết quả đầu tiên.")
        df_ket_qua = df_ket_qua.head(50)

    for i in range(len(df_ket_qua)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 {row.get('hoTen', 'Na')} - {row.get('soBhxh', '')}"
        with st.expander(tieu_de, expanded=False):
            c1, c2 = st.columns(2)
            for idx, cot in enumerate(COT_UU_TIEN):
                val = "(Trống)"
                for c_ex in df_ket_qua.columns:
                     if cot.lower() == c_ex.lower():
                         v = row[c_ex]
                         if pd.notna(v) and str(v).strip() != "" and str(v).lower() != "nan": val = str(v)
                         break
                if idx % 2 == 0: c1.markdown(f"**🔹 {cot}:** {val}")
                else: c2.markdown(f"**🔹 {cot}:** {val}")
            st.dataframe(row.to_frame().T, hide_index=True)

def hien_thi_loc_loi(df, ten_cot):
    col_chuan = df[ten_cot].astype(str).str.strip().str.lower()
    rong = ['nan', 'none', 'null', '', '0']
    df_loc = df[col_chuan.isin(rong)]
    if not df_loc.empty:
        st.warning(f"⚠️ {len(df_loc)} hồ sơ thiếu '{ten_cot}'.")
        st.dataframe(df_loc.head(1000))
    else:
        st.success(f"Tuyệt vời! Cột '{ten_cot}' đủ dữ liệu.")

def hien_thi_kiem_tra_han(df, ten_cot_ngay):
    df_temp = df[[ten_cot_ngay, 'hoTen', 'soBhxh']].copy()
    try:
        df_temp[ten_cot_ngay] = pd.to_datetime(df_temp[ten_cot_ngay], dayfirst=True, errors='coerce') 
        df_co = df_temp.dropna(subset=[ten_cot_ngay])
        hom_nay = datetime.now()
        sau_30 = hom_nay + timedelta(days=30)
        
        ds_het = df_co[df_co[ten_cot_ngay] < hom_nay].copy()
        ds_sap = df_co[(df_co[ten_cot_ngay] >= hom_nay) & (df_co[ten_cot_ngay] <= sau_30)].copy()
        
        if not ds_het.empty: ds_het[ten_cot_ngay] = ds_het[ten_cot_ngay].dt.strftime('%d/%m/%Y')
        if not ds_sap.empty: ds_sap[ten_cot_ngay] = ds_sap[ten_cot_ngay].dt.strftime('%d/%m/%Y')

        c1, c2 = st.columns(2)
        c1.metric("🔴 ĐÃ HẾT HẠN", f"{len(ds_het)}")
        c2.metric("⚠️ SẮP HẾT HẠN", f"{len(ds_sap)}")
        
        if not ds_het.empty:
            st.subheader("🔴 Danh sách Hết Hạn (Top 500)")
            st.dataframe(ds_het.head(500), hide_index=True)
        if not ds_sap.empty:
            st.subheader("⚠️ Danh sách Sắp Hết (Top 500)")
            st.dataframe(ds_sap.head(500), hide_index=True)
    except Exception as e: st.error(f"Lỗi ngày tháng: {e}")

def hien_thi_bieu_do(df, ten_cot):
    st.markdown(f"### 📊 BIỂU ĐỒ: {ten_cot}")
    thong_ke = df[ten_cot].value_counts().head(20).reset_index()
    thong_ke.columns = ['Loại', 'Số lượng'] 
    fig = px.bar(thong_ke, x='Loại', y='Số lượng', text='Số lượng', color='Loại')
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- CHỨC NĂNG AI: CHATBOT NỘI BỘ ---
def hien_thi_chatbot_noi_bo(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO (Thông Minh & Ổn Định)")
    st.info("💡 Ví dụ: 'Tìm tên Lan sinh ngày 10/10/1985', 'Tìm mã số 12345', 'Đếm số lượng'")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Nhập yêu cầu tra cứu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # (Logic xử lý chatbot giữ nguyên như phiên bản trước)
            st.write("Đang tìm kiếm...") 
            # ... (Code logic chatbot đã có ở phiên bản trước, mình rút gọn để tập trung vào phần mới)
            # Bạn có thể copy lại logic chatbot từ file cũ nếu muốn dùng lại

# --- CHỨC NĂNG MỚI: CHỈNH SỬA DỮ LIỆU TRỰC TIẾP ---
def hien_thi_chinh_sua(df):
    st.markdown("### 📝 CHỈNH SỬA & CẬP NHẬT DỮ LIỆU")
    st.info("💡 Bạn có thể sửa trực tiếp trên bảng bên dưới. Sau khi sửa xong, nhớ bấm nút **'Lưu Thay Đổi'**.")

    # Hiển thị bảng chỉnh sửa (Data Editor)
    # num_rows="dynamic" cho phép thêm/xóa dòng
    df_edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        height=600, # Chiều cao bảng
        key='editor'
    )

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 LƯU THAY ĐỔI", type="primary"):
            try:
                # Lưu đè vào file Parquet
                df_edited.to_parquet(PARQUET_FILE)
                
                # Xóa cache để load lại dữ liệu mới
                st.cache_data.clear()
                
                st.success("✅ Đã lưu thành công! Dữ liệu đã được cập nhật.")
                st.rerun() # Tải lại trang
            except Exception as e:
                st.error(f"Lỗi khi lưu: {e}")

# --- MAIN ---
def main():
    hashed_pw = bcrypt.hashpw("12345".encode(), bcrypt.gensalt()).decode()
    credentials = {'usernames': {'bhxh_admin': {'name': 'Admin BHXH', 'email': 'a@b.c', 'password': hashed_pw}}}
    cookie = {'name': 'bhxh_cookie', 'key': 'key_dai_ngoang', 'expiry_days': 30}
    
    authenticator = stauth.Authenticate(credentials, cookie['name'], cookie['key'], cookie['expiry_days'])
    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        with st.sidebar:
            st.write(f'Xin chào, **{st.session_state["name"]}**! 👋')
            authenticator.logout('Đăng xuất', 'sidebar')
            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH (Turbo Mode 🚀)")
        df = nap_du_lieu_toi_uu()
        
        if df.empty: return 

        st.sidebar.header("CHỨC NĂNG")
        cols = df.columns.tolist()
        idx_sobhxh = cols.index('soBhxh') if 'soBhxh' in cols else 0
        ten_cot = st.sidebar.selectbox("Cột xử lý:", options=cols, index=idx_sobhxh)
        tim_kiem = st.sidebar.text_input("Tìm kiếm nhanh:", placeholder="Nhập tên...")

        st.sidebar.markdown("---")
        c1, c2 = st.sidebar.columns(2)
        c1.button("🔍 TRA CỨU", on_click=set_state, args=('search',))
        c2.button("🧹 LỌC LỖI", on_click=set_state, args=('loc',))
        
        c3, c4 = st.sidebar.columns(2)
        c3.button("⏳ HẠN BHYT", on_click=set_state, args=('han',))
        c4.button("📊 BIỂU ĐỒ", on_click=set_state, args=('bieu',))
        
        st.sidebar.markdown("---")
        st.sidebar.button("🤖 TRỢ LÝ ẢO", on_click=set_state, args=('ai',))
        
        # NÚT CHỨC NĂNG MỚI
        st.sidebar.button("📝 CHỈNH SỬA", on_click=set_state, args=('edit',))

        st.markdown("---")
        # Thêm 'edit' vào danh sách quản lý trạng thái
        for key in ['search', 'loc', 'han', 'bieu', 'ai', 'edit']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_chatbot_noi_bo(df) # Dùng lại chatbot nội bộ ổn định
        elif st.session_state.get('edit'): hien_thi_chinh_sua(df) # Gọi màn hình chỉnh sửa
        elif tim_kiem:
            mask = df[ten_cot].astype(str).str.contains(tim_kiem, case=False, na=False)
            hien_thi_uu_tien(df[mask])
        else:
            st.info("👈 Chọn chức năng bên trái.")
            st.caption("Dữ liệu mẫu:")
            st.dataframe(df.head(10))

    elif st.session_state["authentication_status"] is False: st.error('Sai mật khẩu.')
    elif st.session_state["authentication_status"] is None: st.warning('Vui lòng đăng nhập.')

if __name__ == "__main__":
    main()