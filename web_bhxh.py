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

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide")

# --- CẤU HÌNH CSDL ---
DB_FILE = 'bhxh.db'
TEN_BANG = 'ho_so_tham_gia'
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiIh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    for key in ['search', 'loc', 'han', 'bieu', 'chuan']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU ---
@st.cache_data
def nap_du_lieu_tu_csdl():
    # TÊN FILE MỚI: Đuôi .xlsb
    EXCEL_FILE = 'aaa.xlsb' 
    
    if not os.path.exists(DB_FILE):
        if not os.path.exists(EXCEL_FILE):
            st.error(f"❌ Lỗi: Thiếu cả file CSDL ({DB_FILE}) lẫn file Excel ({EXCEL_FILE}).")
            st.info("Vui lòng kiểm tra xem bạn đã upload file 'dữ liệu bhxh.xlsb' lên GitHub chưa.")
            return pd.DataFrame()
        
        try:
            st.warning("⚠️ Đang tự động xây dựng CSDL từ file Excel (.xlsb). Vui lòng đợi...")
            
            # --- THAY ĐỔI QUAN TRỌNG Ở ĐÂY ---
            # Dùng engine='pyxlsb' để đọc file binary excel
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

# --- CÁC HÀM HIỂN THỊ (GIỮ NGUYÊN) ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy hồ sơ nào khớp.")
        return
    st.success(f"✅ Đã tìm thấy {len(df_ket_qua)} hồ sơ!")
    for i in range(len(df_ket_qua)):
        row = df_ket_qua.iloc[i]
        with st.expander(f"👤 HỒ SƠ SỐ {i+1}: {row.get('hoTen', row.get('soBhxh'))}"):
            du_lieu_uu_tien = {}
            for cot_uu_tien in COT_UU_TIEN:
                for col_excel in df_ket_qua.columns:
                     if cot_uu_tien.lower() == col_excel.lower():
                         val = str(row[col_excel]) if pd.notna(row[col_excel]) else "(Trống)"
                         du_lieu_uu_tien[col_excel] = val
                         break
            st.json(du_lieu_uu_tien)
            st.markdown("---")
            st.dataframe(row.to_frame().T)

def hien_thi_loc_loi(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    df_loc = df[df[ten_cot].isna() | (df[ten_cot].str.strip() == "nan") | (df[ten_cot] == "")]
    if not df_loc.empty:
        st.warning(f"⚠️ TÌM THẤY {len(df_loc)} hồ sơ thiếu dữ liệu cột '{ten_cot}'.")
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
        ds_da_het_han = df_co_ngay[df_co_ngay[ten_cot_ngay] < hom_nay]
        ds_sap_het_han = df_co_ngay[(df_co_ngay[ten_cot_ngay] >= hom_nay) & (df_co_ngay[ten_cot_ngay] <= sau_30_ngay)]
        st.markdown("### ⏳ KẾT QUẢ KIỂM TRA HẠN")
        col1, col2 = st.columns(2)
        col1.metric(label="🔴 ĐÃ HẾT HẠN", value=f"{len(ds_da_het_han)} người")
        col2.metric(label="⚠️ SẮP HẾT HẠN (30 ngày)", value=f"{len(ds_sap_het_han)} người")
        if not ds_da_het_han.empty:
            st.subheader("🔴 Danh sách đã Hết Hạn")
            st.dataframe(ds_da_het_han[['hoTen', ten_cot_ngay, 'soBhxh']])
        if not ds_sap_het_han.empty:
            st.subheader("⚠️ Danh sách Sắp Hết Hạn")
            st.dataframe(ds_sap_het_han[['hoTen', ten_cot_ngay, 'soBhxh']])
    except Exception as e:
        st.error(f"Lỗi xử lý ngày tháng. Chi tiết: {e}")

def hien_thi_bieu_do(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    st.markdown("### 📊 BIỂU ĐỒ THỐNG KÊ")
    thong_ke = df[ten_cot].value_counts().head(20)
    st.bar_chart(thong_ke)

# --- PHẦN CHÍNH (MAIN) ---
def main():
    # 1. CẤU HÌNH TÀI KHOẢN (Dùng bcrypt trực tiếp)
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

    cookie = {
        'name': 'bhxh_cookie',
        'key': 'mot_chuoi_ky_tu_ngau_nhien_rat_dai_va_bao_mat_khong_trung_lap',
        'expiry_days': 30
    }

    # 2. Khởi tạo Authenticator
    authenticator = stauth.Authenticate(
        credentials,
        cookie['name'],
        cookie['key'],
        cookie['expiry_days']
    )

    # 3. Hiển thị Form Đăng nhập
    authenticator.login(location='main')

    # 4. Kiểm tra trạng thái
    if st.session_state["authentication_status"]:
        
        # --- GIAO DIỆN CHÍNH ---
        with st.sidebar:
            st.write(f'Xin chào, **{st.session_state["name"]}**! 👋')
            authenticator.logout('Đăng xuất', 'sidebar')
            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH")

        df = nap_du_lieu_tu_csdl()
        if df.empty:
            st.info("Đang chờ dữ liệu...")
            return 

        st.success(f"✅ Hệ thống sẵn sàng: {len(df)} hồ sơ.")

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
        st.sidebar.button("✍️ CHUẨN HÓA", on_click=set_state, args=('chuan',))

        # Logic hiển thị
        st.markdown("---")
        
        for key in ['search', 'loc', 'han', 'bieu', 'chuan']:
            if key not in st.session_state:
                st.session_state[key] = False

        if st.session_state.get('loc'):
            hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'):
            hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'):
            hien_thi_bieu_do(df, ten_cot)
        elif st.session_state.get('chuan'):
            st.warning("Tính năng đang phát triển.")
            st.session_state['chuan'] = False
        elif gia_tri_tim:
            df_tra_cuu = df[df[ten_cot].astype(str).str.contains(gia_tri_tim, case=False, na=False)]
            hien_thi_uu_tien(df_tra_cuu)
        else:
            st.info("👈 Vui lòng chọn chức năng hoặc nhập từ khóa bên trái.")
            st.dataframe(df.head())

    elif st.session_state["authentication_status"] is False:
        st.error('Tên đăng nhập hoặc mật khẩu không đúng.')
    elif st.session_state["authentication_status"] is None:
        st.warning('Vui lòng đăng nhập để tiếp tục.')

if __name__ == "__main__":
    main()