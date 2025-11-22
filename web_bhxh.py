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
import csv # Thư viện ghi file CSV
from datetime import datetime, timedelta
from io import BytesIO
from docx import Document 
from docx.shared import Pt, RGBColor

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide", initial_sidebar_state="expanded")

# --- CẤU HÌNH FILE ---
PARQUET_FILE = 'data_cache.parquet' 
EXCEL_FILE = 'aaa.xlsb' 
USER_DB_FILE = 'users.json' 
LOG_FILE = 'activity_logs.csv' # File lưu nhật ký
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HỆ THỐNG LOGGING (NHẬT KÝ) ---
def log_action(username, action, detail=""):
    """Ghi lại hành động của người dùng vào file CSV"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Kiểm tra nếu file chưa tồn tại thì tạo mới và ghi tiêu đề
    file_exists = os.path.isfile(LOG_FILE)
    
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Thời gian', 'Người dùng', 'Hành động', 'Chi tiết'])
        writer.writerow([timestamp, username, action, detail])

def hien_thi_nhat_ky_he_thong():
    """Hiển thị bảng nhật ký cho Admin"""
    st.markdown("### 🕵️‍♂️ NHẬT KÝ HOẠT ĐỘNG HỆ THỐNG")
    if os.path.exists(LOG_FILE):
        df_log = pd.read_csv(LOG_FILE)
        # Sắp xếp mới nhất lên đầu
        df_log = df_log.sort_values(by='Thời gian', ascending=False)
        st.dataframe(df_log, use_container_width=True, height=500)
        
        # Nút tải về
        csv = df_log.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Tải Nhật ký về máy", csv, "nhat_ky_su_dung.csv", "text/csv")
    else:
        st.info("Chưa có nhật ký hoạt động nào.")

# --- HÀM QUẢN LÝ USER ---
def load_users():
    if not os.path.exists(USER_DB_FILE):
        hashed_pw = bcrypt.hashpw("12345".encode(), bcrypt.gensalt()).decode()
        default_data = {
            'usernames': {
                'bhxh_admin': {
                    'name': 'Admin Tổng',
                    'email': 'admin@bhxh.vn',
                    'password': hashed_pw,
                    'role': 'admin'
                }
            }
        }
        with open(USER_DB_FILE, 'w') as f: json.dump(default_data, f)
        return default_data
    try:
        with open(USER_DB_FILE, 'r') as f: return json.load(f)
    except Exception: return {}

def save_users(config):
    with open(USER_DB_FILE, 'w') as f: json.dump(config, f)

# --- GIAO DIỆN QUẢN TRỊ (ADMIN) ---
def hien_thi_quan_ly_admin(config):
    st.markdown("### ⚙️ TRUNG TÂM QUẢN TRỊ")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Nhật ký Hoạt động", "☁️ Cập nhật Data", "➕ Thêm User", "🔑 Đổi MK User", "❌ Xóa User"])

    # TAB 1: NHẬT KÝ (MỚI)
    with tab1:
        hien_thi_nhat_ky_he_thong()

    # TAB 2: DATA
    with tab2:
        uploaded_file = st.file_uploader("📂 Chọn file Excel dữ liệu (.xlsb)", type=['xlsb'])
        if uploaded_file is not None:
            if st.button("🚀 CẬP NHẬT DỮ LIỆU"):
                try:
                    with st.spinner("Đang xử lý..."):
                        with open(EXCEL_FILE, "wb") as f: f.write(uploaded_file.getbuffer())
                        st.cache_data.clear()
                        if os.path.exists(PARQUET_FILE): os.remove(PARQUET_FILE)
                        nap_du_lieu_toi_uu()
                        log_action(st.session_state["username"], "Cập nhật Data", f"File: {uploaded_file.name}")
                    st.success("✅ Cập nhật thành công!")
                except Exception as e: st.error(f"Lỗi: {e}")

    # TAB 3: THÊM USER
    with tab3:
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            u_new = c1.text_input("User mới")
            n_new = c2.text_input("Tên hiển thị")
            p_new = c1.text_input("Mật khẩu", type="password")
            r_new = c2.selectbox("Quyền", ["user", "admin"])
            if st.form_submit_button("Lưu"):
                if u_new and p_new:
                    if u_new not in config['usernames']:
                        hp = bcrypt.hashpw(p_new.encode(), bcrypt.gensalt()).decode()
                        config['usernames'][u_new] = {'name': n_new, 'password': hp, 'role': r_new, 'email': ''}
                        save_users(config)
                        log_action(st.session_state["username"], "Thêm User", f"User: {u_new}")
                        st.success("✅ Đã thêm.")
                        st.rerun()
                    else: st.error("Trùng tên.")

    # TAB 4: ĐỔI MK
    with tab4:
        u_reset = st.selectbox("Chọn user", list(config['usernames'].keys()), key="rst")
        p_reset = st.text_input("MK mới", type="password", key="prst")
        if st.button("🔄 Đổi mật khẩu"):
            if p_reset:
                hp = bcrypt.hashpw(p_reset.encode(), bcrypt.gensalt()).decode()
                config['usernames'][u_reset]['password'] = hp
                save_users(config)
                log_action(st.session_state["username"], "Đổi MK User", f"User: {u_reset}")
                st.success("✅ Đã đổi.")

    # TAB 5: XÓA USER
    with tab5:
        my_user = st.session_state["username"]
        lst_del = [u for u in config['usernames'].keys() if u != my_user]
        if lst_del:
            u_del = st.selectbox("Chọn xóa", lst_del)
            if st.button("🗑️ Xóa"):
                del config['usernames'][u_del]
                save_users(config)
                log_action(st.session_state["username"], "Xóa User", f"User: {u_del}")
                st.success("✅ Đã xóa.")
                st.rerun()

# --- HÀM HỖ TRỢ ---
def xoa_dau_tieng_viet(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)
    return text

def set_state(name):
    for key in ['search', 'loc', 'han', 'bieu', 'chuan', 'ai', 'admin_panel']:
        st.session_state[key] = False
    st.session_state[name] = True

def tao_file_excel(df_input):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_input.to_excel(writer, index=False, sheet_name='DanhSach')
    writer.close()
    return output

def tao_phieu_word(row):
    doc = Document()
    doc.add_heading('PHIẾU THÔNG TIN BHXH', 0).alignment = 1
    doc.add_paragraph(f'Ngày: {datetime.now().strftime("%d/%m/%Y")}')
    p = doc.add_paragraph()
    run = p.add_run(f"HỌ TÊN: {row.get('hoTen', '').upper()}")
    run.bold = True
    run.font.color.rgb = RGBColor(0, 51, 102)
    table = doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    for cot in COT_UU_TIEN:
        row_cells = table.add_row().cells
        row_cells[0].text = cot
        row_cells[1].text = str(row.get(cot, ''))
    bio = BytesIO()
    doc.save(bio)
    return bio

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

    if not os.path.exists(EXCEL_FILE): return pd.DataFrame()
    try:
        with st.spinner('⚙️ Đang tối ưu hóa...'):
            df = pd.read_excel(EXCEL_FILE, dtype=str, engine='pyxlsb')
            df.columns = df.columns.str.strip()
            df.to_parquet(PARQUET_FILE)
        return df
    except Exception: return pd.DataFrame()

# --- CÁC HÀM HIỂN THỊ (CÓ GẮN LOG) ---
def hien_thi_uu_tien(df_ket_qua):
    st.success(f"✅ Tìm thấy {len(df_ket_qua)} hồ sơ!")
    excel_data = tao_file_excel(df_ket_qua)
    st.download_button("📥 Tải Excel", excel_data.getvalue(), "ds.xlsx")
    
    for i in range(min(len(df_ket_qua), 50)):
        row = df_ket_qua.iloc[i]
        tieu_de = f"👤 {row.get('hoTen', 'Na')} - {row.get('soBhxh', '')}"
        with st.expander(tieu_de, expanded=False):
            c1, c2 = st.columns([3, 1])
            with c1:
                col_a, col_b = st.columns(2)
                for idx, cot in enumerate(COT_UU_TIEN):
                    val = str(row.get(cot, ''))
                    if idx % 2 == 0: col_a.markdown(f"**🔹 {cot}:** {val}")
                    else: col_b.markdown(f"**🔹 {cot}:** {val}")
            with c2:
                w_data = tao_phieu_word(row)
                if st.download_button("📄 In Phiếu", w_data.getvalue(), f"P_{i}.docx", key=f"w_{i}"):
                    log_action(st.session_state["username"], "In Phiếu", row.get('hoTen', ''))
            st.dataframe(row.to_frame().T, hide_index=True)

def hien_thi_loc_loi(df, ten_cot):
    # Log hành động
    log_action(st.session_state["username"], "Lọc Lỗi", f"Cột: {ten_cot}")
    
    col_chuan = df[ten_cot].astype(str).str.strip().str.lower()
    rong = ['nan', 'none', 'null', '', '0']
    df_loc = df[col_chuan.isin(rong)]
    if not df_loc.empty:
        st.warning(f"⚠️ {len(df_loc)} hồ sơ thiếu '{ten_cot}'.")
        excel_data = tao_file_excel(df_loc)
        st.download_button("📥 Tải lỗi", excel_data.getvalue(), f"loi_{ten_cot}.xlsx")
        st.dataframe(df_loc.head(1000))
    else: st.success(f"Tuyệt vời! Cột '{ten_cot}' đủ dữ liệu.")

def hien_thi_kiem_tra_han(df, ten_cot_ngay):
    # Log hành động
    log_action(st.session_state["username"], "Kiểm tra hạn", ten_cot_ngay)
    
    df_temp = df[[ten_cot_ngay, 'hoTen', 'soBhxh']].copy()
    try:
        df_temp[ten_cot_ngay] = pd.to_datetime(df_temp[ten_cot_ngay], dayfirst=True, errors='coerce') 
        df_co = df_temp.dropna(subset=[ten_cot_ngay])
        hom_nay = datetime.now()
        sau_30 = hom_nay + timedelta(days=30)
        ds_het = df_co[df_co[ten_cot_ngay] < hom_nay]
        ds_sap = df_co[(df_co[ten_cot_ngay] >= hom_nay) & (df_co[ten_cot_ngay] <= sau_30)]
        
        c1, c2 = st.columns(2)
        c1.metric("🔴 ĐÃ HẾT HẠN", f"{len(ds_het)}")
        c2.metric("⚠️ SẮP HẾT HẠN", f"{len(ds_sap)}")
        
        if not ds_het.empty:
            st.subheader("🔴 Danh sách Hết Hạn")
            e_het = tao_file_excel(ds_het)
            st.download_button("📥 Tải Hết Hạn", e_het.getvalue(), "het_han.xlsx")
            st.dataframe(ds_het.head(500), hide_index=True)
        if not ds_sap.empty:
            st.subheader("⚠️ Danh sách Sắp Hết")
            e_sap = tao_file_excel(ds_sap)
            st.download_button("📥 Tải Sắp Hết", e_sap.getvalue(), "sap_het.xlsx")
            st.dataframe(ds_sap.head(500), hide_index=True)
    except Exception: st.error("Lỗi ngày tháng")

def hien_thi_bieu_do_tuong_tac(df, ten_cot):
    # Log hành động
    log_action(st.session_state["username"], "Xem Biểu Đồ", ten_cot)
    
    st.markdown(f"### 📊 BIỂU ĐỒ: {ten_cot}")
    thong_ke = df[ten_cot].value_counts().reset_index()
    thong_ke.columns = ['Phân loại', 'Số lượng'] 
    fig = px.bar(thong_ke, x='Phân loại', y='Số lượng', text='Số lượng', color='Phân loại')
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")
    if event and event['selection']['points']:
        gia_tri = event['selection']['points'][0]['x']
        st.info(f"🔍 Đang xem: **{gia_tri}**.")
        # Log hành động xem chi tiết
        log_action(st.session_state["username"], "Click Biểu Đồ", f"Xem: {gia_tri}")
        hien_thi_uu_tien(df[df[ten_cot] == gia_tri])

def hien_thi_chatbot_thong_minh(df):
    st.markdown("### 🤖 TRỢ LÝ ẢO")
    if "messages" not in st.session_state: st.session_state.messages = []
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    if prompt := st.chat_input("Nhập yêu cầu..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        
        # Log câu hỏi
        log_action(st.session_state["username"], "Chat AI", prompt)
        
        with st.chat_message("assistant"):
            msg_bot = []
            p_clean = xoa_dau_tieng_viet(prompt)
            df_res = df.copy()
            df_res['hoTen_khongdau'] = df_res['hoTen'].apply(lambda x: xoa_dau_tieng_viet(str(x)))
            filters = [] 
            try:
                date_m = re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{4}', prompt)
                if date_m:
                    nr = date_m.group().replace('-', '/')
                    try:
                        nd = pd.to_datetime(nr, dayfirst=True).strftime('%d/%m/%Y')
                        df_res = df_res[df_res['ngaySinh'].astype(str).str.contains(nd)]
                        filters.append(f"Ngày sinh: {nd}")
                        p_clean = p_clean.replace(xoa_dau_tieng_viet(nr), "")
                    except: pass
                nums = re.findall(r'\b\d{5,}\b', prompt)
                for n in nums:
                    if date_m and n in date_m.group(): continue
                    df_res = df_res[(df_res['soBhxh'].astype(str).str.contains(n)) | (df_res['soCmnd'].astype(str).str.contains(n))]
                    filters.append(f"Mã: {n}")
                    p_clean = p_clean.replace(n, "")
                
                tu_rac = ["tim", "loc", "cho", "toi", "nguoi", "co", "ngay", "sinh", "ten", "la", "o", "que"]
                for w in tu_rac: p_clean = re.sub(r'\b' + w + r'\b', '', p_clean)
                p_clean = re.sub(r'\b(bieu do|thong ke|han|het han)\b', '', p_clean)
                ten = re.sub(r'\s+', ' ', p_clean).strip()
                
                if len(ten) > 1:
                    df_res = df_res[df_res['hoTen_khongdau'].str.contains(ten)]
                    filters.append(f"Tên: {ten}")

                if "bieu do" in xoa_dau_tieng_viet(prompt):
                    col = 'gioiTinh'
                    if "tinh" in p_clean: col = 'maTinh'
                    if "huyen" in p_clean: col = 'maHuyen'
                    st.write(f"📈 Biểu đồ: {col}")
                    hien_thi_bieu_do_tuong_tac(df, col)
                elif filters:
                    st.write(f"🔍 Lọc: {' + '.join(filters)}")
                    if not df_res.empty:
                        if 'hoTen_khongdau' in df_res.columns: df_res = df_res.drop(columns=['hoTen_khongdau'])
                        hien_thi_uu_tien(df_res)
                    else: st.warning("Không tìm thấy.")
                else: st.info("Hãy nhập tên hoặc ngày sinh.")
            except Exception as e: st.error(f"Lỗi: {e}")

# --- MAIN ---
def main():
    user_config = load_users()
    authenticator = stauth.Authenticate(user_config, 'bhxh_cookie', 'key_123', 30)
    name, authentication_status, username = authenticator.login(location='main')

    if st.session_state["authentication_status"]:
        # GHI LOG ĐĂNG NHẬP (Chỉ ghi 1 lần mỗi phiên)
        if 'logged_in' not in st.session_state:
            log_action(username, "Đăng nhập", "Thành công")
            st.session_state['logged_in'] = True

        user_role = user_config['usernames'][username].get('role', 'user')
        user_display = user_config['usernames'][username]['name']

        with st.sidebar:
            st.write(f'Xin chào, **{user_display}**! 👋')
            if user_role == 'admin': st.caption("👑 Admin")
            else: st.caption("👤 User")
            
            if st.button("Đăng xuất"):
                log_action(username, "Đăng xuất", "")
                authenticator.logout('main')

            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH")
        df = nap_du_lieu_toi_uu()
        
        if df.empty:
            st.warning("⚠️ Chưa có dữ liệu.")
            if user_role == 'admin':
                st.sidebar.button("⚙️ QUẢN TRỊ", on_click=set_state, args=('admin_panel',))
                if st.session_state.get('admin_panel'): hien_thi_quan_ly_admin(user_config)
            return

        st.sidebar.header("CHỨC NĂNG")
        cols = df.columns.tolist()
        idx_so = cols.index('soBhxh') if 'soBhxh' in cols else 0
        ten_cot = st.sidebar.selectbox("Cột xử lý:", options=cols, index=idx_so)
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
        
        if user_role == 'admin':
            st.sidebar.markdown("---")
            st.sidebar.button("⚙️ QUẢN TRỊ", on_click=set_state, args=('admin_panel',))

        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'ai', 'admin_panel']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do_tuong_tac(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_chatbot_thong_minh(df)
        elif st.session_state.get('admin_panel') and user_role == 'admin': hien_thi_quan_ly_admin(user_config)
        elif tim_kiem:
            # Log tìm kiếm nhanh
            log_action(username, "Tìm kiếm nhanh", f"Từ khóa: {tim_kiem} (Cột: {ten_cot})")
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