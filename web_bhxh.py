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
from io import BytesIO
from docx import Document 
from docx.shared import Pt, RGBColor

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH FILE ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' 
USER_DB_FILE = 'users.json' # File lưu danh sách tài khoản
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HÀM QUẢN LÝ USER (MỚI) ---
def load_users():
    """Đọc danh sách user từ file JSON. Nếu chưa có thì tạo Admin mặc định."""
    if not os.path.exists(USER_DB_FILE):
        # Tạo Admin mặc định: bhxh_admin / 12345
        hashed_pw = bcrypt.hashpw("12345".encode(), bcrypt.gensalt()).decode()
        default_data = {
            'usernames': {
                'bhxh_admin': {
                    'name': 'Admin Tổng',
                    'email': 'admin@bhxh.vn',
                    'password': hashed_pw,
                    'role': 'admin' # Quyền cao nhất
                }
            }
        }
        with open(USER_DB_FILE, 'w') as f:
            json.dump(default_data, f)
        return default_data
    
    try:
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_users(config):
    """Lưu danh sách user mới vào file JSON"""
    with open(USER_DB_FILE, 'w') as f:
        json.dump(config, f)

# --- GIAO DIỆN QUẢN LÝ USER (CHỈ ADMIN THẤY) ---
def hien_thi_quan_ly_user(config):
    st.markdown("### 👥 QUẢN LÝ NGƯỜI DÙNG")
    st.info("💡 Tại đây bạn có thể thêm tài khoản cho nhân viên mới.")

    # 1. Form thêm người dùng
    with st.form("add_user_form"):
        st.subheader("Thêm tài khoản mới")
        c1, c2 = st.columns(2)
        new_username = c1.text_input("Tên đăng nhập (Viết liền, không dấu)", placeholder="vd: nhanvien1")
        new_name = c2.text_input("Tên hiển thị", placeholder="vd: Nguyễn Văn A")
        new_password = c1.text_input("Mật khẩu", type="password")
        new_role = c2.selectbox("Phân quyền", ["user", "admin"], index=0, help="'user' chỉ được xem, 'admin' được quản lý hệ thống")
        
        submitted = st.form_submit_button("Lưu tài khoản")
        
        if submitted:
            if new_username and new_password and new_name:
                if new_username in config['usernames']:
                    st.error("❌ Tên đăng nhập này đã tồn tại!")
                else:
                    # Mã hóa mật khẩu
                    hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                    
                    # Thêm vào data
                    config['usernames'][new_username] = {
                        'name': new_name,
                        'password': hashed_pw,
                        'role': new_role,
                        'email': ''
                    }
                    save_users(config) # Lưu xuống file
                    st.success(f"✅ Đã tạo thành công user: {new_username} ({new_role})")
            else:
                st.warning("⚠️ Vui lòng điền đầy đủ thông tin.")

    # 2. Danh sách người dùng hiện có
    st.divider()
    st.subheader("Danh sách tài khoản hiện có")
    
    # Chuyển dict sang list để hiển thị bảng
    user_list = []
    for u, data in config['usernames'].items():
        user_list.append({
            "Tên đăng nhập": u,
            "Tên hiển thị": data['name'],
            "Quyền": data.get('role', 'user')
        })
    st.dataframe(pd.DataFrame(user_list), use_container_width=True)


# --- HÀM HỖ TRỢ CHUNG ---
def xoa_dau_tieng_viet(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def set_state(name):
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai', 'admin_data', 'admin_user']:
        st.session_state[key] = False
    st.session_state[name] = True

# --- HÀM XỬ LÝ FILE WORD/EXCEL (GIỮ NGUYÊN) ---
def tao_phieu_word(row):
    doc = Document()
    heading = doc.add_heading('PHIẾU THÔNG TIN BHXH', 0)
    heading.alignment = 1 
    doc.add_paragraph(f'Ngày xuất phiếu: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    doc.add_paragraph('--------------------------------------------------')
    p = doc.add_paragraph()
    run = p.add_run(f"HỌ VÀ TÊN: {row.get('hoTen', '').upper()}")
    run.bold = True
    run.font.size = Pt(14)
    run.font.color.rgb = RGBColor(0, 51, 102)
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'THÔNG TIN'
    hdr_cells[1].text = 'CHI TIẾT'
    for cot in COT_UU_TIEN:
        row_cells = table.add_row().cells
        row_cells[0].text = cot
        val = row.get(cot, '')
        row_cells[1].text = str(val) if pd.notna(val) else ""
    doc.add_paragraph('\n')
    doc.add_paragraph('Người trích xuất: Admin BHXH').alignment = 2
    bio = BytesIO()
    doc.save(bio)
    return bio

def tao_file_excel(df_input):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_input.to_excel(writer, index=False, sheet_name='DanhSach')
    writer.close()
    return output

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

# --- GIAO DIỆN QUẢN TRỊ DATA (CHỈ ADMIN THẤY) ---
def hien_thi_quan_tri_data():
    st.markdown("### ⚙️ CẬP NHẬT DỮ LIỆU HỆ THỐNG")
    uploaded_file = st.file_uploader("📂 Chọn file Excel dữ liệu (.xlsb)", type=['xlsb'])
    if uploaded_file is not None:
        if st.button("🚀 CẬP NHẬT DỮ LIỆU"):
            try:
                with st.spinner("Đang xử lý..."):
                    with open(EXCEL_FILE, "wb") as f: f.write(uploaded_file.getbuffer())
                    st.cache_data.clear()
                    if os.path.exists(PARQUET_FILE): os.remove(PARQUET_FILE)
                    nap_du_lieu_toi_uu()
                st.success("✅ Cập nhật thành công!")
                st.balloons()
            except Exception as e: st.error(f"Có lỗi xảy ra: {e}")

# --- CÁC HÀM HIỂN THỊ (GIỮ NGUYÊN) ---
def hien_thi_uu_tien(df_ket_qua):
    if df_ket_qua.empty:
        st.warning("😞 Không tìm thấy kết quả.")
        return
    st.success(f"✅ Tìm thấy {len(df_ket_qua)} hồ sơ!")
    excel_data = tao_file_excel(df_ket_qua)
    st.download_button(label="📥 Tải Excel", data=excel_data.getvalue(), file_name=f"danh_sach.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    if len(df_ket_qua) > 50: st.caption(f"⚠️ Đang hiển thị 50/{len(df_ket_qua)} kết quả đầu tiên.")
    for i in range(min(len(df_ket_qua), 50)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 {row.get('hoTen', 'Na')} - {row.get('soBhxh', '')}"
        with st.expander(tieu_de, expanded=False):
            c1, c2 = st.columns([3, 1])
            with c1:
                col_a, col_b = st.columns(2)
                for idx, cot in enumerate(COT_UU_TIEN):
                    val = "(Trống)"
                    for c_ex in df_ket_qua.columns:
                         if cot.lower() == c_ex.lower():
                             v = row[c_ex]
                             if pd.notna(v) and str(v).strip() != "" and str(v).lower() != "nan": val = str(v)
                             break
                    if idx % 2 == 0: col_a.markdown(f"**🔹 {cot}:** {val}")
                    else: col_b.markdown(f"**🔹 {cot}:** {val}")
            with c2:
                word_data = tao_phieu_word(row)
                st.download_button(label="📄 In Phiếu", data=word_data.getvalue(), file_name=f"Phieu_{row.get('soBhxh', 'hs')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", key=f"btn_word_{i}")
            st.dataframe(row.to_frame().T, hide_index=True)

def hien_thi_loc_loi(df, ten_cot):
    col_chuan = df[ten_cot].astype(str).str.strip().str.lower()
    rong = ['nan', 'none', 'null', '', '0']
    df_loc = df[col_chuan.isin(rong)]
    if not df_loc.empty:
        st.warning(f"⚠️ {len(df_loc)} hồ sơ thiếu '{ten_cot}'.")
        excel_data = tao_file_excel(df_loc)
        st.download_button(label="📥 Tải danh sách lỗi", data=excel_data.getvalue(), file_name=f"loi_{ten_cot}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(df_loc.head(1000))
    else: st.success(f"Tuyệt vời! Cột '{ten_cot}' đủ dữ liệu.")

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
            st.subheader("🔴 Danh sách Hết Hạn")
            excel_het = tao_file_excel(ds_het)
            st.download_button("📥 Tải DS Hết Hạn", excel_het.getvalue(), "ds_het_han.xlsx")
            st.dataframe(ds_het.head(500), hide_index=True)
        if not ds_sap.empty:
            st.subheader("⚠️ Danh sách Sắp Hết")
            excel_sap = tao_file_excel(ds_sap)
            st.download_button("📥 Tải DS Sắp Hết", excel_sap.getvalue(), "ds_sap_het.xlsx")
            st.dataframe(ds_sap.head(500), hide_index=True)
    except Exception as e: st.error(f"Lỗi ngày tháng: {e}")

def hien_thi_bieu_do_tuong_tac(df, ten_cot):
    st.markdown(f"### 📊 BIỂU ĐỒ TƯƠNG TÁC: {ten_cot}")
    thong_ke = df[ten_cot].value_counts().reset_index()
    thong_ke.columns = ['Phân loại', 'Số lượng'] 
    fig = px.bar(thong_ke, x='Phân loại', y='Số lượng', text='Số lượng', color='Phân loại')
    fig.update_traces(textposition='outside')
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
    if event and event['selection']['points']:
        gia_tri_chon = event['selection']['points'][0]['x']
        st.divider()
        st.info(f"🔍 Bạn vừa chọn: **{gia_tri_chon}**.")
        df_loc = df[df[ten_cot] == gia_tri_chon]
        hien_thi_uu_tien(df_loc)
    else: st.info("💡 Mẹo: Nhấp vào cột biểu đồ để xem chi tiết.")

def hien_thi_chatbot_thong_minh(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO (Tìm Kiếm Linh Hoạt)")
    st.info("💡 Ví dụ: 'Lan 12/5/2012', 'tìm hùng', 'vẽ biểu đồ giới tính'")
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if prompt := st.chat_input("Nhập yêu cầu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            msg_bot = []
            prompt_khong_dau = xoa_dau_tieng_viet(prompt)
            df_result = df.copy()
            df_result['hoTen_khongdau'] = df_result['hoTen'].apply(lambda x: xoa_dau_tieng_viet(str(x)))
            filters = [] 
            try:
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
                numbers = re.findall(r'\b\d{5,}\b', prompt)
                for num in numbers:
                    if date_match and num in date_match.group(): continue
                    mask_so = (df_result['soBhxh'].astype(str).str.contains(num)) | (df_result['soCmnd'].astype(str).str.contains(num))
                    df_result = df_result[mask_so]
                    filters.append(f"Mã số: **{num}**")
                    prompt_khong_dau = prompt_khong_dau.replace(num, "")
                tu_rac = ["tim", "loc", "cho", "toi", "nguoi", "co", "ngay", "sinh", "ten", "la", "o", "que"]
                for w in tu_rac: prompt_khong_dau = re.sub(r'\b' + w + r'\b', '', prompt_khong_dau)
                prompt_khong_dau = re.sub(r'\b(bieu do|thong ke|han|het han)\b', '', prompt_khong_dau)
                ten_can_tim = re.sub(r'\s+', ' ', prompt_khong_dau).strip()
                if len(ten_can_tim) > 1:
                    df_result = df_result[df_result['hoTen_khongdau'].str.contains(ten_can_tim)]
                    filters.append(f"Tên chứa: **{ten_can_tim}**")
                if "bieu do" in xoa_dau_tieng_viet(prompt):
                    cot_ve = 'gioiTinh'
                    if "tinh" in xoa_dau_tieng_viet(prompt): cot_ve = 'maTinh'
                    if "huyen" in xoa_dau_tieng_viet(prompt): cot_ve = 'maHuyen'
                    st.write(f"📈 Đang vẽ biểu đồ: {cot_ve}")
                    hien_thi_bieu_do_tuong_tac(df, cot_ve)
                elif "han" in xoa_dau_tieng_viet(prompt):
                    st.write("⏳ Đang kiểm tra hạn BHYT...")
                    hien_thi_kiem_tra_han(df, 'hanTheDen')
                elif filters:
                    st.write(f"🔍 Điều kiện: {' + '.join(filters)}")
                    if not df_result.empty:
                        if 'hoTen_khongdau' in df_result.columns: df_result = df_result.drop(columns=['hoTen_khongdau'])
                        hien_thi_uu_tien(df_result)
                    else: st.warning("Không tìm thấy ai.")
                else: st.info("🤖 Hãy nhập tên hoặc ngày sinh để tìm kiếm.")
            except Exception as e: st.error(f"Lỗi xử lý: {e}")

# --- MAIN ---
def main():
    # 1. Load User từ file JSON
    user_config = load_users()
    
    # 2. Khởi tạo Authenticator
    authenticator = stauth.Authenticate(
        user_config, # Load từ config động
        'bhxh_cookie', 
        'key_bi_mat_rat_dai_va_kho_doan_123', 
        30
    )
    authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        # Lấy thông tin user hiện tại
        username = st.session_state["username"]
        user_role = user_config['usernames'][username].get('role', 'user') # Mặc định là user nếu ko có role
        user_name_display = user_config['usernames'][username]['name']

        with st.sidebar:
            st.write(f'Xin chào, **{user_name_display}**! 👋')
            if user_role == 'admin':
                st.caption("👑 Quản trị viên")
            else:
                st.caption("👤 Người dùng")
                
            authenticator.logout('Đăng xuất', 'sidebar')
            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH")
        df = nap_du_lieu_toi_uu()
        
        if df.empty:
            st.warning("⚠️ Chưa có dữ liệu.")
            if user_role == 'admin': # Chỉ admin mới thấy nút này khi chưa có data
                st.sidebar.button("⚙️ CẬP NHẬT DATA", on_click=set_state, args=('admin_data',))
                if st.session_state.get('admin_data'): hien_thi_quan_tri_data()
            return

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
        
        # --- CHỈ ADMIN MỚI THẤY NÚT QUẢN TRỊ ---
        if user_role == 'admin':
            st.sidebar.markdown("---")
            st.sidebar.caption("QUẢN TRỊ HỆ THỐNG")
            st.sidebar.button("⚙️ CẬP NHẬT DATA", on_click=set_state, args=('admin_data',))
            st.sidebar.button("👥 QUẢN LÝ USER", on_click=set_state, args=('admin_user',))

        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'ai', 'admin_data', 'admin_user']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do_tuong_tac(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_chatbot_thong_minh(df)
        # Chỉ admin mới vào được 2 hàm này
        elif st.session_state.get('admin_data') and user_role == 'admin': hien_thi_quan_tri_data()
        elif st.session_state.get('admin_user') and user_role == 'admin': hien_thi_quan_ly_user(user_config)
        
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