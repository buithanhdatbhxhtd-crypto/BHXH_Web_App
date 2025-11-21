import streamlit as st
import pandas as pd
import sqlite3
from sqlalchemy import create_engine
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# --- CẤU HÌNH CSDL ---
DB_FILE = 'bhxh.db'
TEN_BANG = 'ho_so_tham_gia'
# Danh sách cột ưu tiên
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChilh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK CHO NÚT BẤM (Cần đặt ở đây) ---
# Hàm này sẽ được gọi khi nút bấm được nhấn để lưu lại hành động vào session state
def set_state(name):
    # Đặt tất cả các trạng thái khác về False, chỉ đặt trạng thái nút vừa bấm về True
    for key in ['search', 'loc', 'han', 'bieu']:
        st.session_state[key] = False 
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU (CHẠY 1 LẦN) ---
@st.cache_data
def nap_du_lieu_tu_csdl():
    # 1. Nếu CSDL chưa tồn tại, đọc file Excel và tạo CSDL
    DB_FILE = 'bhxh.db'
    EXCEL_FILE = 'data_bhxh.xlsx'
    TEN_BANG = 'ho_so_tham_gia'

    if not os.path.exists(DB_FILE):
        if not os.path.exists(EXCEL_FILE):
            st.error(f"❌ Lỗi: Thiếu cả file CSDL ({DB_FILE}) lẫn file Excel ({EXCEL_FILE}).")
            return pd.DataFrame()
        
        # Nếu thiếu DB, tự động tạo DB từ Excel
        try:
            st.warning("⚠️ Đang tự động xây dựng CSDL từ file Excel. Vui lòng đợi...")
            df_init = pd.read_excel(EXCEL_FILE, dtype=str, engine='openpyxl')
            df_init.columns = df_init.columns.str.strip()
            
            engine = create_engine(f'sqlite:///{DB_FILE}')
            df_init.to_sql(TEN_BANG, engine, if_exists='replace', index=False)
            engine.dispose()
            st.success("✅ CSDL đã được xây dựng thành công trên máy chủ Streamlit.")
        except Exception as e:
            st.error(f"❌ Lỗi tạo CSDL: {e}")
            return pd.DataFrame()

    # 2. Đọc dữ liệu từ CSDL (Chạy nhanh sau khi tạo xong)
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql(f"SELECT * FROM {TEN_BANG}", conn)
        conn.close()
        df.columns = df.columns.str.strip() 
        return df.astype(str)
    except Exception:
        return pd.DataFrame()

# --- HÀM XUẤT KẾT QUẢ ƯU TIÊN ---
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

# --- HÀM LỌC DỮ LIỆU LỖI/TRỐNG ---
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

# --- HÀM KIỂM TRA HẠN BHYT ---
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
        st.metric(label="🔴 ĐÃ HẾT HẠN", value=f"{len(ds_da_het_han)} người")
        st.metric(label="⚠️ SẮP HẾT HẠN (30 ngày tới)", value=f"{len(ds_sap_het_han)} người")

        if not ds_da_het_han.empty:
            st.dataframe(ds_da_het_han)
        if not ds_sap_het_han.empty:
            st.dataframe(ds_sap_het_han)

    except Exception as e:
        st.error(f"Lỗi xử lý ngày tháng. Chi tiết: {e}")

# --- HÀM VẼ BIỂU ĐỒ ---
def hien_thi_bieu_do(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    
    st.markdown("### 📊 BIỂU ĐỒ THỐNG KÊ")
    thong_ke = df[ten_cot].value_counts().head(20)
    st.bar_chart(thong_ke)
    st.dataframe(thong_ke)

# --- PHẦN CHÍNH (MAIN) ---
def main():
    st.set_page_config(page_title="BHXH Web Manager", layout="wide")
    st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH - PHIÊN BẢN WEB")
    
    df = nap_du_lieu_tu_csdl()

    if df.empty:
        st.error("❌ Ứng dụng không thể tải dữ liệu. Hãy kiểm tra file CSDL 'bhxh.db'.")
        return

    st.success(f"✅ Đã tải xong {len(df)} dòng dữ liệu. Hệ thống sẵn sàng.")
    
    # 1. THANH SIDEBAR (ĐỊNH NGHĨA UI - VỊ TRÍ CHUẨN)
    st.sidebar.header("CHỨC NĂNG")
    
    danh_sach_cot = df.columns.tolist()
    
    # LƯU Ý QUAN TRỌNG: st.session_state để lưu input (Fix bug)
    ten_cot = st.sidebar.selectbox(
        "Chọn Cột Xử Lý/Tra Cứu:",
        options=danh_sach_cot, 
        index=danh_sach_cot.index("soBhxh") if "soBhxh" in danh_sach_cot else 0
    )
    
    gia_tri_tim = st.sidebar.text_input(f"Nhập Giá Trị Tra Cứu:", placeholder=f"Ví dụ: Nguyễn Thị Loan")

    # 2. KHU VỰC NÚT BẤM (Buttons)
    st.sidebar.markdown("---")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.button("🔍 TRA CỨU HỒ SƠ", on_click=set_state, args=('search',)) 
    with col2:
        st.button("🧹 LỌC DỮ LIỆU LỖI", on_click=set_state, args=('loc',))
        
    col3, col4 = st.sidebar.columns(2)
    with col3:
        st.button("⏳ KIỂM TRA HẠN", on_click=set_state, args=('han',))
    with col4:
        st.button("📊 VẼ BIỂU ĐỒ", on_click=set_state, args=('bieu',))

    st.sidebar.markdown("---") 
    st.sidebar.button("✍️ CHUẨN HÓA DỮ LIỆU", on_click=set_state, args=('chuan',)) 

    # 3. LOGIC HIỂN THỊ CHÍNH (MAIN DISPLAY)
    st.markdown("---")
    
    # Khai báo biến tạm thời (Đảm bảo an toàn)
    ten_cot_hien_tai = ten_cot
    gia_tri_hien_tai = gia_tri_tim

    if st.session_state.get('loc'):
        hien_thi_loc_loi(df, ten_cot_hien_tai)
    
    elif st.session_state.get('han'):
        hien_thi_kiem_tra_han(df, ten_cot_hien_tai)

    elif st.session_state.get('bieu'):
        hien_thi_bieu_do(df, ten_cot_hien_tai)

    elif st.session_state.get('chuan'):
        st.warning("Tính năng Chuẩn hóa đang được kích hoạt. Hãy xem Terminal.")
        # Logic xử lý chuẩn hóa ở đây
        st.session_state['chuan'] = False
        st.experimental_rerun()
        
    elif gia_tri_hien_tai: # Tự động tra cứu khi gõ chữ
        df_tra_cuu = df[df[ten_cot_hien_tai].str.contains(gia_tri_hien_tai, case=False, na=False)]
        hien_thi_uu_tien(df_tra_cuu)
    
    else:
        st.subheader("Dữ liệu cơ bản:")
        st.dataframe(df.head())


if __name__ == "__main__":
    for key in ['search', 'loc', 'han', 'bieu', 'chuan']:
        if key not in st.session_state:
            st.session_state[key] = False
    
    main()