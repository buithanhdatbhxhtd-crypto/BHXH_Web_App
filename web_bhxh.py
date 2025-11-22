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
from datetime import datetime, timedelta

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH FILE ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' 
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

def hien_thi_bieu_do(df, ten_cot):
    st.markdown(f"### 📊 BIỂU ĐỒ: {ten_cot}")
    thong_ke = df[ten_cot].value_counts().head(20).reset_index()
    thong_ke.columns = ['Loại', 'Số lượng'] 
    fig = px.bar(thong_ke, x='Loại', y='Số lượng', text='Số lượng', color='Loại')
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- CHATBOT THÔNG MINH (ĐÃ FIX LỖI NHẬN DIỆN SAI) ---
def hien_thi_chatbot_thong_minh(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO (Tìm Kiếm Linh Hoạt)")
    st.info("💡 Bạn cứ nhập tự nhiên: 'Lan 22/01/1988', 'tìm Bùi Thành Đạt', 'số thẻ 12345'")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Nhập thông tin cần tìm..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # 1. Chuẩn bị
            df_result = df.copy()
            df_result['hoTen_khongdau'] = df_result['hoTen'].apply(lambda x: xoa_dau_tieng_viet(str(x)))
            prompt_khong_dau = xoa_dau_tieng_viet(prompt)
            
            msg_bot = [] 
            found_filter = False # Cờ đánh dấu xem có tìm thấy điều kiện lọc nào không

            try:
                # --- BƯỚC 1: ƯU TIÊN TÌM NGÀY THÁNG ---
                # Tìm chuỗi số/số/số hoặc số-số-số
                date_match = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', prompt)
                if date_match:
                    ngay_nhap = date_match.group().replace('-', '/')
                    try:
                        date_obj = pd.to_datetime(ngay_nhap, dayfirst=True)
                        ngay_chuan = date_obj.strftime('%d/%m/%Y')
                        
                        # Lọc ngày
                        mask_date = df_result['ngaySinh'].astype(str).str.contains(ngay_chuan)
                        df_result = df_result[mask_date]
                        
                        msg_bot.append(f"📅 Ngày sinh: **{ngay_chuan}**")
                        found_filter = True
                        
                        # Xóa ngày khỏi câu lệnh để tránh nhiễu khi tìm tên
                        prompt_khong_dau = prompt_khong_dau.replace(xoa_dau_tieng_viet(ngay_nhap), "").strip()
                    except: pass

                # --- BƯỚC 2: TÌM MÃ SỐ ---
                numbers = re.findall(r'\b\d{5,}\b', prompt)
                for num in numbers:
                    if date_match and num in date_match.group(): continue
                    
                    mask_so = (df_result['soBhxh'].astype(str).str.contains(num)) | \
                              (df_result['soCmnd'].astype(str).str.contains(num))
                    df_result = df_result[mask_so]
                    msg_bot.append(f"🔢 Mã số: **{num}**")
                    found_filter = True
                    prompt_khong_dau = prompt_khong_dau.replace(num, "").strip()

                # --- BƯỚC 3: TÌM TÊN (PHẦN CÒN LẠI) ---
                # Xóa từ khóa rác, giữ lại tên
                tu_rac = ["tim", "loc", "cho", "toi", "nguoi", "co", "ngay", "sinh", "ten", "la", "o", "que"]
                for w in tu_rac:
                    prompt_khong_dau = re.sub(r'\b' + w + r'\b', '', prompt_khong_dau)
                
                # Loại bỏ lệnh chức năng khỏi phần tên để tránh tìm nhầm
                prompt_khong_dau = re.sub(r'\b(bieu do|thong ke|han|het han)\b', '', prompt_khong_dau)
                
                ten_can_tim = re.sub(r'\s+', ' ', prompt_khong_dau).strip()
                
                if len(ten_can_tim) > 1: # Tên phải dài hơn 1 ký tự mới tìm
                    df_result = df_result[df_result['hoTen_khongdau'].str.contains(ten_can_tim)]
                    msg_bot.append(f"🔤 Tên chứa: **{ten_can_tim}**")
                    found_filter = True

                # --- BƯỚC 4: QUYẾT ĐỊNH HIỂN THỊ ---
                # Nếu ĐÃ CÓ điều kiện lọc (Tên hoặc Ngày hoặc Mã) -> Ưu tiên hiển thị kết quả tìm kiếm
                if found_filter:
                    st.write(f"🔍 Đang lọc theo: {' + '.join(msg_bot)}")
                    if not df_result.empty:
                        if 'hoTen_khongdau' in df_result.columns:
                            df_result = df_result.drop(columns=['hoTen_khongdau'])
                        hien_thi_uu_tien(df_result)
                    else:
                        st.warning("Không tìm thấy hồ sơ nào khớp với tất cả điều kiện trên.")
                
                # Nếu KHÔNG CÓ điều kiện lọc nào -> Mới kiểm tra lệnh chức năng
                else:
                    cmd_clean = xoa_dau_tieng_viet(prompt)
                    if "bieu do" in cmd_clean:
                        cot_ve = 'gioiTinh'
                        if "tinh" in cmd_clean: cot_ve = 'maTinh'
                        st.write(f"📈 Đang vẽ biểu đồ: {cot_ve}")
                        hien_thi_bieu_do(df, cot_ve)
                    elif "han" in cmd_clean and "het" in cmd_clean: # Phải có chữ 'hết hạn' mới chạy
                        st.write("⏳ Đang kiểm tra hạn BHYT...")
                        hien_thi_kiem_tra_han(df, 'hanTheDen')
                    else:
                        st.info("🤖 Hãy nhập tên hoặc ngày sinh để tìm kiếm.")

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
        tim_kiem = st.sidebar.text_input("Tìm kiếm nhanh (Cột đã chọn):", placeholder="Nhập...")

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
        elif st.session_state.get('bieu'): hien_thi_bieu_do(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_chatbot_thong_minh(df) # Đã cập nhật Logic
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