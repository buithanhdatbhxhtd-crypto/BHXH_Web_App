import streamlit as st
import pandas as pd
import os
import streamlit_authenticator as stauth
import yaml
import bcrypt
import plotly.express as px
import requests # Thư viện gửi yêu cầu trực tiếp
import json

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' 
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU (TURBO MODE) ---
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

# --- CÁC HÀM HIỂN THỊ CƠ BẢN ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy hồ sơ.")
        return
    st.success(f"✅ Tìm thấy {len(df_ket_qua)} hồ sơ!")
    
    hien_thi_max = 50
    if len(df_ket_qua) > hien_thi_max:
        st.warning(f"⚠️ Chỉ hiện {hien_thi_max} kết quả đầu để mượt.")
        df_ket_qua = df_ket_qua.head(hien_thi_max)

    for i in range(len(df_ket_qua)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 HỒ SƠ: {row.get('hoTen', 'Na')} - {row.get('soBhxh', '')}"
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
            st.caption("Gốc:")
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

# --- CHỨC NĂNG AI: CƠ CHẾ TỰ ĐỘNG TÌM MODEL (FIX DỨT ĐIỂM) ---
def call_gemini_smart(api_key, prompt):
    # Danh sách các model sẽ thử lần lượt
    models_to_try = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-pro"]
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    # Thử từng model
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            
            # Nếu thành công (200 OK) -> Trả về kết quả ngay
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            
            # Nếu lỗi 404 (Không tìm thấy model) -> Bỏ qua, thử model tiếp theo
            elif response.status_code == 404:
                continue 
                
            # Nếu lỗi khác (ví dụ sai Key) -> Báo lỗi ngay
            else:
                return f"Lỗi từ Google ({model_name}): {response.text}"
                
        except Exception as e:
            continue # Lỗi mạng thì thử cái tiếp theo

    return "Xin lỗi, hệ thống đã thử tất cả các phiên bản AI nhưng đều thất bại. Vui lòng kiểm tra lại API Key của bạn."

def hien_thi_tro_ly_ai_lite(df):
    st.markdown("### 🤖 TRỢ LÝ AI (Bản Nhẹ & Thông Minh)")
    st.info("💡 AI sẽ tự động chọn phiên bản tốt nhất để trả lời bạn.")

    # API Key CỦA BẠN (Đã điền sẵn)
    API_KEY = "AIzaSyCN6rglQb1-Ay7fwwo5rtle8q4xZemw550"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Hỏi gì đó về dữ liệu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI đang suy nghĩ..."):
                # Chuẩn bị dữ liệu (Dùng to_string để tránh lỗi tabulate)
                data_sample = df.head(10).to_string(index=False)
                columns_info = ", ".join(df.columns.tolist())
                total_rows = len(df)
                
                context = f"""
                Bạn là trợ lý dữ liệu BHXH. Thông tin bộ dữ liệu:
                - Tổng số dòng: {total_rows}
                - Các cột: {columns_info}
                - Dữ liệu mẫu (10 dòng đầu):
                {data_sample}
                
                Câu hỏi người dùng: "{prompt}"
                Hãy trả lời ngắn gọn, hữu ích bằng tiếng Việt.
                """
                
                # Gọi hàm thông minh mới
                tra_loi = call_gemini_smart(API_KEY, context)
                
                st.write(tra_loi)
                st.session_state.messages.append({"role": "assistant", "content": tra_loi})

# --- MAIN ---
def main():
    # Mật khẩu 12345
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
        tim_kiem = st.sidebar.text_input("Tìm kiếm:", placeholder="Nhập tên...")

        st.sidebar.markdown("---")
        c1, c2 = st.sidebar.columns(2)
        c1.button("🔍 TRA CỨU", on_click=set_state, args=('search',))
        c2.button("🧹 LỌC LỖI", on_click=set_state, args=('loc',))
        
        c3, c4 = st.sidebar.columns(2)
        c3.button("⏳ HẠN BHYT", on_click=set_state, args=('han',))
        c4.button("📊 BIỂU ĐỒ", on_click=set_state, args=('bieu',))
        
        st.sidebar.markdown("---")
        st.sidebar.button("🤖 TRỢ LÝ AI", on_click=set_state, args=('ai',))

        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'ai']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_tro_ly_ai_lite(df)
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