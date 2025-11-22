import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import streamlit_authenticator as stauth
import yaml
import bcrypt
import plotly.express as px

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH ---
# Dùng file .parquet để load siêu nhanh (Cache file)
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' # File gốc của bạn

COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM TẠO CALLBACK ---
def set_state(name):
    # Reset các trạng thái khác
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM NẠP DỮ LIỆU TỐI ƯU (DÙNG PARQUET) ---
@st.cache_data(ttl=3600) # Cache dữ liệu trong 1 giờ để không phải load lại
def nap_du_lieu_toi_uu():
    # 1. Ưu tiên đọc file Parquet (Siêu nhanh)
    if os.path.exists(PARQUET_FILE):
        try:
            df = pd.read_parquet(PARQUET_FILE)
            # Đảm bảo các cột quan trọng là dạng chuỗi để tránh lỗi
            cols_to_str = ['soBhxh', 'soCmnd', 'soDienThoai']
            for col in cols_to_str:
                if col in df.columns:
                    df[col] = df[col].astype(str)
            return df
        except Exception:
            pass # Nếu lỗi file parquet thì đọc lại excel

    # 2. Nếu chưa có Parquet, đọc Excel (Lần đầu sẽ chậm)
    if not os.path.exists(EXCEL_FILE):
        st.error(f"❌ Không tìm thấy file dữ liệu gốc: {EXCEL_FILE}")
        return pd.DataFrame()
    
    try:
        with st.spinner('⚙️ Đang tối ưu hóa dữ liệu lần đầu (Chuyển sang Parquet)... Vui lòng đợi...'):
            # Đọc file .xlsb
            df = pd.read_excel(EXCEL_FILE, dtype=str, engine='pyxlsb')
            df.columns = df.columns.str.strip()
            
            # Lưu lại thành Parquet để lần sau chạy nhanh hơn
            df.to_parquet(PARQUET_FILE)
            st.toast("✅ Đã tạo bộ nhớ đệm siêu tốc!", icon="🚀")
            
        return df
    except Exception as e:
        st.error(f"❌ Lỗi đọc file Excel: {e}")
        return pd.DataFrame()

# --- CÁC HÀM HIỂN THỊ ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy hồ sơ nào khớp.")
        return
    st.success(f"✅ Đã tìm thấy {len(df_ket_qua)} hồ sơ!")
    
    # Chỉ hiển thị tối đa 50 kết quả để tránh lag trình duyệt
    hien_thi_max = 50
    if len(df_ket_qua) > hien_thi_max:
        st.warning(f"⚠️ Chỉ hiển thị {hien_thi_max} kết quả đầu tiên để đảm bảo tốc độ.")
        df_ket_qua = df_ket_qua.head(hien_thi_max)

    for i in range(len(df_ket_qua)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 HỒ SƠ: {row.get('hoTen', 'Không tên')} - {row.get('soBhxh', '')}"
        with st.expander(tieu_de, expanded=False): # expanded=False để đóng bớt cho gọn
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
        st.warning(f"⚠️ TÌM THẤY {len(df_loc)} hồ sơ thiếu dữ liệu cột '{ten_cot}'.")
        st.dataframe(df_loc.head(1000)) # Chỉ hiện 1000 dòng lỗi đầu tiên
    else:
        st.success(f"Tuyệt vời! Cột '{ten_cot}' đầy đủ dữ liệu.")

def hien_thi_kiem_tra_han(df, ten_cot_ngay):
    if ten_cot_ngay not in df.columns:
        st.error(f"❌ Không tìm thấy cột: '{ten_cot_ngay}'.")
        return
    
    # Xử lý trên bản sao nhẹ hơn
    df_temp = df[[ten_cot_ngay, 'hoTen', 'soBhxh']].copy()
    
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
            st.subheader("🔴 Danh sách đã Hết Hạn (Top 500)")
            st.dataframe(ds_da_het_han.head(500), hide_index=True)
        if not ds_sap_het_han.empty:
            st.subheader("⚠️ Danh sách Sắp Hết Hạn (Top 500)")
            st.dataframe(ds_sap_het_han.head(500), hide_index=True)
    except Exception as e:
        st.error(f"Lỗi xử lý ngày tháng. Chi tiết: {e}")

def hien_thi_bieu_do(df, ten_cot):
    if ten_cot not in df.columns:
        st.error(f"❌ Không tìm thấy cột '{ten_cot}'.")
        return
    st.markdown(f"### 📊 BIỂU ĐỒ THỐNG KÊ: {ten_cot}")
    
    # Giới hạn số lượng nhóm để biểu đồ không bị đơ nếu quá nhiều loại
    thong_ke = df[ten_cot].value_counts().head(20).reset_index()
    thong_ke.columns = ['Phân loại', 'Số lượng'] 
    
    fig = px.bar(thong_ke, x='Phân loại', y='Số lượng', text='Số lượng', color='Phân loại', title=f"Top 20 phân loại theo {ten_cot}")
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

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
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH (Turbo Mode 🚀)")
        
        # Load dữ liệu tối ưu
        df = nap_du_lieu_toi_uu()
        
        if df.empty:
            st.info("Đang chờ dữ liệu...")
            return 

        # Sidebar chức năng
        st.sidebar.header("CHỨC NĂNG")
        danh_sach_cot = df.columns.tolist()
        
        # Chọn cột thông minh (ưu tiên soBhxh)
        idx_sobhxh = 0
        if 'soBhxh' in danh_sach_cot:
            idx_sobhxh = danh_sach_cot.index('soBhxh')
            
        ten_cot = st.sidebar.selectbox("Cột tra cứu/xử lý:", options=danh_sach_cot, index=idx_sobhxh)
        gia_tri_tim = st.sidebar.text_input("Từ khóa tìm kiếm:", placeholder="Ví dụ: Nguyễn Văn A")

        st.sidebar.markdown("---")
        c1, c2 = st.sidebar.columns(2)
        c1.button("🔍 TRA CỨU", on_click=set_state, args=('search',))
        c2.button("🧹 LỌC LỖI", on_click=set_state, args=('loc',))
        
        c3, c4 = st.sidebar.columns(2)
        c3.button("⏳ HẠN BHYT", on_click=set_state, args=('han',))
        c4.button("📊 BIỂU ĐỒ", on_click=set_state, args=('bieu',))
        
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
        elif gia_tri_tim:
            # Tìm kiếm tối ưu: Chuyển về chuỗi và tìm
            mask = df[ten_cot].astype(str).str.contains(gia_tri_tim, case=False, na=False)
            df_tra_cuu = df[mask]
            hien_thi_uu_tien(df_tra_cuu)
        else:
            st.info("👈 Vui lòng chọn chức năng hoặc nhập từ khóa.")
            # Không hiển thị toàn bộ 100k dòng để tránh lag, chỉ hiện top 10
            st.caption("Dữ liệu mẫu (10 dòng đầu):")
            st.dataframe(df.head(10))

    elif st.session_state["authentication_status"] is False:
        st.error('Tên đăng nhập hoặc mật khẩu không đúng.')
    elif st.session_state["authentication_status"] is None:
        st.warning('Vui lòng đăng nhập để tiếp tục.')

if __name__ == "__main__":
    main()