import streamlit as st
import pandas as pd
import os
import streamlit_authenticator as stauth
import yaml
import bcrypt
import plotly.express as px
import requests 
import json
import re
import unicodedata

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH FILE ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'data.xlsb' 
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM HỖ TRỢ: XÓA DẤU TIẾNG VIỆT ---
def xoa_dau_tieng_viet(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU ---
@st.cache_data(ttl=3600)
def nap_du_lieu_toi_uu():
    if os.path.exists(PARQUET_FILE):
        try:
            df = pd.read_parquet(PARQUET_FILE)
            cols_to_str = ['soBhxh', 'soCmnd', 'soDienThoai', 'ngaySinh', 'hanTheDen']
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

# --- NÂNG CẤP: BIỂU ĐỒ TƯƠNG TÁC (Drill-down) ---
def hien_thi_bieu_do_tuong_tac(df, ten_cot):
    st.markdown(f"### 📊 BIỂU ĐỒ TƯƠNG TÁC: {ten_cot}")
    
    # 1. Thống kê dữ liệu
    thong_ke = df[ten_cot].value_counts().reset_index()
    thong_ke.columns = ['Phân loại', 'Số lượng'] 
    
    # 2. Vẽ biểu đồ
    fig = px.bar(thong_ke, x='Phân loại', y='Số lượng', text='Số lượng', color='Phân loại')
    fig.update_traces(textposition='outside')
    
    # 3. Hiển thị biểu đồ và BẮT SỰ KIỆN CLICK
    # on_select="rerun" sẽ chạy lại app khi bạn click vào cột
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # 4. Xử lý khi người dùng Click
    if event and event['selection']['points']:
        # Lấy giá trị của cột vừa click (ví dụ: 'Nam' hoặc 'Huyện A')
        # Plotly trả về danh sách điểm, ta lấy điểm đầu tiên
        gia_tri_chon = event['selection']['points'][0]['x']
        
        st.divider()
        st.info(f"🔍 Bạn vừa chọn: **{gia_tri_chon}**. Dưới đây là danh sách chi tiết:")
        
        # Lọc dữ liệu theo giá trị đã chọn
        df_loc = df[df[ten_cot] == gia_tri_chon]
        
        # Hiển thị danh sách bằng hàm ưu tiên có sẵn
        hien_thi_uu_tien(df_loc)
        
    else:
        st.info("💡 Mẹo: Hãy **nhấp chuột vào một cột** trên biểu đồ để xem danh sách chi tiết những người thuộc nhóm đó.")

# --- CHATBOT THÔNG MINH ---
def hien_thi_chatbot_thong_minh(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO (Tìm Kiếm Linh Hoạt)")
    st.info("💡 Ví dụ: 'Tìm tên Lan sinh ngày 10/10/1985', 'Tìm mã số 12345'")

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
            msg_bot = ""
            prompt_khong_dau = xoa_dau_tieng_viet(prompt)
            df_result = df.copy()
            df_result['hoTen_khongdau'] = df_result['hoTen'].apply(lambda x: xoa_dau_tieng_viet(str(x)))
            filters = [] 

            try:
                # Logic Ngày tháng
                date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', prompt)
                if date_match:
                    ngay_raw = date_match.group().replace('-', '/')
                    try:
                        date_obj = pd.to_datetime(ngay_raw, dayfirst=True)
                        ngay_chuan = date_obj.strftime('%d/%m/%Y')
                        mask_date = df_result['ngaySinh'].astype(str).str.contains(ngay_chuan)
                        df_result = df_result[mask_date]
                        filters.append(f"Ngày sinh: **{ngay_chuan}**")
                        prompt_khong_dau = prompt_khong_dau.replace(xoa_dau_tieng_viet(ngay_raw), "")
                    except: pass

                # Logic Mã số
                numbers = re.findall(r'\b\d{5,}\b', prompt)
                for num in numbers:
                    if date_match and num in date_match.group(): continue
                    mask_so = (df_result['soBhxh'].astype(str).str.contains(num)) | \
                              (df_result['soCmnd'].astype(str).str.contains(num))
                    df_result = df_result[mask_so]
                    filters.append(f"Mã số: **{num}**")
                    prompt_khong_dau = prompt_khong_dau.replace(num, "")

                # Logic Tên
                tu_khoa_rac = ["tim", "loc", "cho", "toi", "nguoi", "co", "ngay", "sinh", "ten", "la", "o", "que"]
                for w in tu_khoa_rac: prompt_khong_dau = re.sub(r'\b' + w + r'\b', '', prompt_khong_dau)
                
                ten_can_tim = prompt_khong_dau.strip()
                if len(ten_can_tim) > 1 and "bieu do" not in ten_can_tim and "han" not in ten_can_tim:
                    mask_ten = df_result['hoTen_khongdau'].str.contains(ten_can_tim)
                    df_result = df_result[mask_ten]
                    filters.append(f"Tên chứa: **{ten_can_tim}**")

                # Tổng hợp
                if "bieu do" in xoa_dau_tieng_viet(prompt):
                    cot_ve = 'gioiTinh'
                    if "tinh" in prompt_khong_dau: cot_ve = 'maTinh'
                    if "huyen" in prompt_khong_dau: cot_ve = 'maHuyen'
                    st.write(f"📈 Đang vẽ biểu đồ: {cot_ve}")
                    hien_thi_bieu_do_tuong_tac(df, cot_ve) # Gọi hàm biểu đồ mới
                elif "han" in xoa_dau_tieng_viet(prompt):
                    st.write("⏳ Đang kiểm tra hạn BHYT...")
                    hien_thi_kiem_tra_han(df, 'hanTheDen')
                elif filters:
                    st.write(f"🔍 Điều kiện: {' + '.join(filters)}")
                    st.write(f"👉 Kết quả: **{len(df_result)}** hồ sơ.")
                    if not df_result.empty:
                        if 'hoTen_khongdau' in df_result.columns: df_result = df_result.drop(columns=['hoTen_khongdau'])
                        st.dataframe(df_result.head(50))
                    else:
                        st.warning("Không tìm thấy ai.")
                else:
                    st.info("🤖 Hãy thử: 'Tìm Lan 12/5/2012', 'Vẽ biểu đồ', 'Kiểm tra hạn'")

            except Exception as e:
                st.error(f"Lỗi xử lý: {e}")

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

        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'ai']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do_tuong_tac(df, ten_cot) # Dùng hàm mới
        elif st.session_state.get('ai'): hien_thi_chatbot_thong_minh(df)
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
