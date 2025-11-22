import streamlit as st
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import streamlit_authenticator as stauth
import yaml
import bcrypt
import plotly.express as px
from pandasai import SmartDataframe
from pandasai.llm import GoogleGemini

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide")

# --- CẤU HÌNH CSDL ---
DB_FILE = 'bhxh.db'
TEN_BANG = 'ho_so_tham_gia'
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    # Reset các trạng thái khác
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU ---
@st.cache_data
def nap_du_lieu_tu_csdl():
    EXCEL_FILE = 'data.xlsb'
    
    if not os.path.exists(DB_FILE):
        if not os.path.exists(EXCEL_FILE):
            st.error(f"❌ Lỗi: Thiếu cả file CSDL ({DB_FILE}) lẫn file Excel ({EXCEL_FILE}).")
            return pd.DataFrame()
        
        try:
            st.warning("⚠️ Đang tự động xây dựng CSDL từ file Excel. Vui lòng đợi...")
            df_init = pd.read_excel(EXCEL_FILE, dtype=str, engine='pyxlsb')
            df_init.columns = df_init.columns.str.strip()
            
            engine = create_engine(f'sqlite:///{DB_FILE}')
            df_init.to_sql(TEN_BANG, engine, if_exists='replace', index=False)
            engine.dispose()
            st.success("✅ CSDL đã được xây dựng thành công.")
        except Exception as e:
            st.error(f"❌ Lỗi tạo CSDL: {e}")
            return pd.DataFrame()

    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql(f"SELECT * FROM {TEN_BANG}", conn)
        conn.close()
        df.columns = df.columns.str.strip() 
        return df.astype(str)
    except Exception:
        return pd.DataFrame()

# --- CÁC HÀM HIỂN THỊ CŨ (GIỮ NGUYÊN) ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy hồ sơ nào khớp.")
        return
    st.success(f"✅ Đã tìm thấy {len(df_ket_qua)} hồ sơ!")
    for i in range(len(df_ket_qua)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 HỒ SƠ SỐ {i+1}: {row.get('hoTen', 'Không tên')} - Mã: {row.get('soBhxh', '---')}"
        with st.expander(tieu_de, expanded=True):
            c1, c2 = st.columns(2)
            for idx, cot_uu_tien in enumerate(COT_UU_TIEN):
                gia_tri = "(Trống)"
                for col_excel in df_ket_qua.columns:
                     if cot_uu_tien.lower() == col_excel.lower():
                         val = row[col_excel]
                         if pd.notna(val) and str(val).strip() != "" and str(val).lower() != "nan":
                             gia_tri = str(val)
                         break
                noi_dung = f"**🔹 {cot_uu_tien}:** {gia_tri}"
                if idx % 2 == 0: c1.markdown(noi_dung)
                else: c2.markdown(noi_dung)
            st.markdown("---")
            st.caption("Dữ liệu gốc:")
            st.dataframe(row.to_frame().T, hide_index=True)

def hien_thi_loc_loi(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    col_chuan_hoa = df[ten_cot].astype(str).str.strip().str.lower()
    gia_tri_rong = ['nan', 'none', 'null', '', '0']
    df_loc = df[col_chuan_hoa.isin(gia_tri_rong)]
    if not df_loc.empty:
        st.warning(f"⚠️ TÌM THẤY {len(df_loc)} hồ sơ thiếu dữ liệu ở cột '{ten_cot}'.")
        st.dataframe(df_loc)
    else:
        st.success(f"Tuyệt vời! Cột '{ten_cot}' đầy đủ dữ liệu.")

def hien_thi_kiem_tra_han(df, ten_cot_ngay):
    if ten_cot_ngay not in df.columns:
        st.error(f"❌ Không tìm thấy cột Ngày Hết Hạn: '{ten_cot_ngay}'.")
        return
    df_temp = df.copy()
    try:
        df_temp[ten_cot_ngay] = pd.to_datetime(df_temp[ten_cot_ngay], dayfirst=True, errors='coerce') 
        df_co_ngay = df_temp.dropna(subset=[ten_cot_ngay])
        hom_nay = datetime.now()
        sau_30_ngay = hom_nay + timedelta(days=30)
        ds_da_het_han = df_co_ngay[df_co_ngay[ten_cot_ngay] < hom_nay].copy()
        ds_sap_het_han = df_co_ngay[(df_co_ngay[ten_cot_ngay] >= hom_nay) & (df_co_ngay[ten_cot_ngay] <= sau_30_ngay)].copy()
        
        if not ds_da_het_han.empty:
            ds_da_het_han[ten_cot_ngay] = ds_da_het_han[ten_cot_ngay].dt.strftime('%d/%m/%Y')
        if not ds_sap_het_han.empty:
            ds_sap_het_han[ten_cot_ngay] = ds_sap_het_han[ten_cot_ngay].dt.strftime('%d/%m/%Y')

        st.markdown("### ⏳ KẾT QUẢ KIỂM TRA HẠN")
        col1, col2 = st.columns(2)
        col1.metric(label="🔴 ĐÃ HẾT HẠN", value=f"{len(ds_da_het_han)} người")
        col2.metric(label="⚠️ SẮP HẾT HẠN (30 ngày)", value=f"{len(ds_sap_het_han)} người")
        if not ds_da_het_han.empty:
            st.subheader("🔴 Danh sách đã Hết Hạn")
            st.dataframe(ds_da_het_han[['hoTen', ten_cot_ngay, 'soBhxh']], hide_index=True)
        if not ds_sap_het_han.empty:
            st.subheader("⚠️ Danh sách Sắp Hết Hạn")
            st.dataframe(ds_sap_het_han[['hoTen', ten_cot_ngay, 'soBhxh']], hide_index=True)
    except Exception as e:
        st.error(f"Lỗi xử lý ngày tháng. Chi tiết: {e}")

def hien_thi_bieu_do(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    st.markdown(f"### 📊 BIỂU ĐỒ THỐNG KÊ: {ten_cot}")
    thong_ke = df[ten_cot].value_counts().reset_index()
    thong_ke.columns = ['Phân loại', 'Số lượng'] 
    fig = px.bar(thong_ke, x='Phân loại', y='Số lượng', text='Số lượng', color='Phân loại', title=f"Phân bố theo {ten_cot}")
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# --- CHỨC NĂNG MỚI: TRỢ LÝ ẢO AI ---
def hien_thi_tro_ly_ai(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO AI (Chat với Dữ liệu)")
    st.info("💡 Bạn có thể hỏi: 'Có bao nhiêu người tên Lan?', 'Vẽ biểu đồ giới tính', hoặc 'Ai sắp hết hạn thẻ?'")
    
    # 1. Cấu hình API Key (DÁN KEY CỦA BẠN VÀO DÒNG DƯỚI)
    api_key = "AIzaSyCN6rglQb1-Ay7fwwo5rtle8q4xZemw550" 
    
    if api_key == "AIzaSyCN6rglQb1-Ay7fwwo5rtle8q4xZemw550":
        st.warning("⚠️ Vui lòng nhập Google API Key vào code web_bhxh.py để sử dụng tính năng này.")
        return

    # 2. Khởi tạo AI
    llm = GoogleGemini(api_key=api_key)
    sdf = SmartDataframe(df, config={"llm": llm})

    # 3. Giao diện Chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Hiển thị lịch sử chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Ô nhập liệu
    if prompt := st.chat_input("Nhập câu hỏi của bạn về dữ liệu BHXH..."):
        # Hiển thị câu hỏi của người dùng
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI suy nghĩ và trả lời
        with st.chat_message("assistant"):
            with st.spinner("AI đang phân tích dữ liệu..."):
                try:
                    response = sdf.chat(prompt)
                    st.write(response) # Dùng st.write để hiển thị cả văn bản lẫn biểu đồ nếu có
                    st.session_state.messages.append({"role": "assistant", "content": str(response)})
                except Exception as e:
                    st.error(f"AI gặp lỗi: {e}")


# --- PHẦN CHÍNH (MAIN) ---
def main():
    # 1. ĐĂNG NHẬP
    mat_khau_raw = "12345"
    hashed_pw = bcrypt.hashpw(mat_khau_raw.encode(), bcrypt.gensalt()).decode()
    
    credentials = {
        'usernames': {
            'bhxh_admin': {
                'name': 'Admin BHXH',
                'email': 'admin@bhxh.vn',
                'password': hashed_pw 
            }
        }
    }
    cookie = {'name': 'bhxh_cookie', 'key': 'key_bao_mat_rat_dai', 'expiry_days': 30}
    authenticator = stauth.Authenticate(credentials, cookie['name'], cookie['key'], cookie['expiry_days'])
    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        with st.sidebar:
            st.write(f'Xin chào, **{st.session_state["name"]}**! 👋')
            authenticator.logout('Đăng xuất', 'sidebar')
            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH")
        df = nap_du_lieu_tu_csdl()
        
        if df.empty:
            st.info("Đang chờ dữ liệu...")
            return 

        # Sidebar chức năng
        st.sidebar.header("CHỨC NĂNG")
        danh_sach_cot = df.columns.tolist()
        ten_cot = st.sidebar.selectbox("Cột tra cứu/xử lý:", options=danh_sach_cot, index=0)
        gia_tri_tim = st.sidebar.text_input("Từ khóa tìm kiếm:", placeholder="Ví dụ: Nguyễn Văn A")

        st.sidebar.markdown("---")
        c1, c2 = st.sidebar.columns(2)
        c1.button("🔍 TRA CỨU", on_click=set_state, args=('search',))
        c2.button("🧹 LỌC LỖI", on_click=set_state, args=('loc',))
        
        c3, c4 = st.sidebar.columns(2)
        c3.button("⏳ HẠN BHYT", on_click=set_state, args=('han',))
        c4.button("📊 BIỂU ĐỒ", on_click=set_state, args=('bieu',))
        
        st.sidebar.markdown("---")
        # Nút Trợ lý AI mới
        st.sidebar.button("🤖 TRỢ LÝ AI", on_click=set_state, args=('ai',))

        # Logic hiển thị
        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'):
            hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'):
            hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'):
            hien_thi_bieu_do(df, ten_cot)
        elif st.session_state.get('ai'):
            hien_thi_tro_ly_ai(df) # Gọi hàm AI mới
        elif gia_tri_tim:
            df_tra_cuu = df[df[ten_cot].astype(str).str.contains(gia_tri_tim, case=False, na=False)]
            hien_thi_uu_tien(df_tra_cuu)
        else:
            st.info("👈 Vui lòng chọn chức năng bên trái.")
            st.dataframe(df.head())

    elif st.session_state["authentication_status"] is False:
        st.error('Tên đăng nhập hoặc mật khẩu không đúng.')
    elif st.session_state["authentication_status"] is None:
        st.warning('Vui lòng đăng nhập để tiếp tục.')

if __name__ == "__main__":
    main()