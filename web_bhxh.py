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
import csv 
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
LOG_FILE = 'activity_logs.csv' 
COT_UU_TIEN = ['hoTen', 'ngaySinh', 'soBhxh', 'hanTheDen', 'soCmnd', 'soDienThoai', 'diaChiLh', 'VSS_EMAIL']

# --- HỆ THỐNG LOGGING (NHẬT KÝ) ---
def log_action(username, action, detail=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(['Thời gian', 'Người dùng', 'Hành động', 'Chi tiết'])
        writer.writerow([timestamp, username, action, detail])

def hien_thi_nhat_ky_he_thong():
    st.markdown("### 🕵️‍♂️ NHẬT KÝ HOẠT ĐỘNG HỆ THỐNG")
    if os.path.exists(LOG_FILE):
        df_log = pd.read_csv(LOG_FILE)
        df_log = df_log.sort_values(by='Thời gian', ascending=False)
        st.dataframe(df_log, use_container_width=True, height=500)
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

# --- GIAO DIỆN QUẢN TRỊ USER (ADMIN) ---
def hien_thi_quan_ly_user(config):
    st.markdown("### 👥 QUẢN TRỊ NGƯỜI DÙNG")
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Thêm User", "🛠️ Reset Mật khẩu", "🔑 Đổi MK Thủ công", "❌ Xóa User"])

    # TAB 1: THÊM USER
    with tab1:
        st.info("💡 Tạo tài khoản mới cho nhân viên.")
        with st.form("add_user_form"):
            c1, c2 = st.columns(2)
            new_username = c1.text_input("Tên đăng nhập (Viết liền)", placeholder="vd: nhanvien1")
            new_name = c2.text_input("Tên hiển thị", placeholder="vd: Nguyễn Văn A")
            new_password = c1.text_input("Mật khẩu khởi tạo", type="password")
            new_role = c2.selectbox("Phân quyền", ["user", "admin"], index=0)
            
            if st.form_submit_button("Lưu tài khoản"):
                if new_username and new_password and new_name:
                    if new_username in config['usernames']:
                        st.error("❌ Tên đăng nhập này đã tồn tại!")
                    else:
                        hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
                        config['usernames'][new_username] = {
                            'name': new_name,
                            'password': hashed_pw,
                            'role': new_role,
                            'email': ''
                        }
                        save_users(config)
                        log_action(st.session_state["username"], "Thêm User", f"User: {new_username}")
                        st.success(f"✅ Đã tạo user: {new_username}")
                        st.rerun()
                else:
                    st.warning("⚠️ Vui lòng điền đủ thông tin.")

    # TAB 2: RESET MẬT KHẨU VỀ MẶC ĐỊNH
    with tab2:
        st.warning("⚠️ Chức năng này sẽ đặt lại mật khẩu của user về mặc định là: **123456**")
        
        list_users = list(config['usernames'].keys())
        col_res_1, col_res_2 = st.columns([3, 1])
        
        with col_res_1:
            user_to_reset = st.selectbox("Chọn tài khoản cần Reset:", list_users, key="sel_reset")
        
        with col_res_2:
            st.write("") 
            st.write("")
            if st.button("🔄 Reset về 123456", type="primary"):
                try:
                    default_pw_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
                    config['usernames'][user_to_reset]['password'] = default_pw_hash
                    save_users(config)
                    log_action(st.session_state["username"], "Reset MK", f"User: {user_to_reset}")
                    st.success(f"✅ Đã reset mật khẩu của **{user_to_reset}** thành **123456**")
                except Exception as e:
                    st.error(f"Lỗi: {e}")

    # TAB 3: ĐỔI MẬT KHẨU (ADMIN TỰ ĐỔI CHO MÌNH HOẶC NGƯỜI KHÁC)
    with tab3:
        st.info("Đổi mật khẩu thủ công sang một mật khẩu mới cụ thể.")
        list_all_users = list(config['usernames'].keys())
        
        col_change_1, col_change_2 = st.columns([3, 1])
        with col_change_1:
            user_to_change = st.selectbox("Chọn tài khoản:", list_all_users, key="sel_change")
            new_pass_change = st.text_input("Nhập mật khẩu mới:", type="password", key="new_pass_change")
        
        with col_change_2:
            st.write("") 
            st.write("") 
            if st.button("💾 Cập nhật MK"):
                if new_pass_change:
                    new_hash = bcrypt.hashpw(new_pass_change.encode(), bcrypt.gensalt()).decode()
                    config['usernames'][user_to_change]['password'] = new_hash
                    save_users(config)
                    log_action(st.session_state["username"], "Đổi MK thủ công", f"User: {user_to_change}")
                    st.success(f"✅ Đã đổi mật khẩu cho: {user_to_change}")
                else:
                    st.error("Chưa nhập mật khẩu.")

    # TAB 4: XÓA USER
    with tab4:
        st.error("⚠️ Hành động xóa không thể hoàn tác.")
        current_user = st.session_state["username"]
        list_users_to_delete = [u for u in config['usernames'].keys() if u != current_user]
        
        if list_users_to_delete:
            col_del_1, col_del_2 = st.columns([3, 1])
            with col_del_1:
                user_to_delete = st.selectbox("Chọn tài khoản cần xóa:", list_users_to_delete, key="sel_del")
            with col_del_2:
                st.write("") 
                st.write("")
                if st.button("🗑️ Xác nhận xóa", type="primary"):
                    try:
                        del config['usernames'][user_to_delete]
                        save_users(config)
                        log_action(st.session_state["username"], "Xóa User", f"User: {user_to_delete}")
                        st.success(f"✅ Đã xóa tài khoản: {user_to_delete}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Lỗi: {e}")
        else:
            st.info("Không có tài khoản nào khác để xóa.")

    # HIỂN THỊ DANH SÁCH
    st.divider()
    st.subheader("Danh sách tài khoản hiện có")
    user_list = []
    for u, data in config['usernames'].items():
        user_list.append({
            "Tên đăng nhập": u,
            "Tên hiển thị": data['name'],
            "Quyền hạn": data.get('role', 'user'),
            "Trạng thái mật khẩu": "Đã mã hóa (Ẩn)"
        })
    st.dataframe(pd.DataFrame(user_list), use_container_width=True)


# --- CÁC HÀM XỬ LÝ DỮ LIỆU CÒN LẠI (GIỮ NGUYÊN) ---
# ... (hàm xoa_dau_tieng_viet, set_state, tao_phieu_word, tao_file_excel, nap_du_lieu_toi_uu, hien_thi_quan_tri_data, hien_thi_uu_tien, hien_thi_loc_loi, hien_thi_kiem_tra_han, hien_thi_bieu_do_tuong_tac, hien_thi_chatbot_thong_minh đều được giữ nguyên)

# --- PHẦN LOGIC CHÍNH ---
def main():
    # 1. Load User
    user_config = load_users()
    
    # 2. Khởi tạo Authenticator
    authenticator = stauth.Authenticate(user_config, 'bhxh_cookie', 'key_bi_mat_rat_dai_va_kho_doan_123', 30)
    
    # 3. FIX: Gọi login mà không lấy giá trị trả về
    authenticator.login(location='main') # <--- LỖI ĐÃ ĐƯỢC FIX TẠI ĐÂY (BỎ UNPACKING)

    if st.session_state["authentication_status"]:
        # GHI LOG ĐĂNG NHẬP (Chỉ ghi 1 lần)
        if 'logged_in' not in st.session_state:
            log_action(st.session_state["username"], "Đăng nhập", "Thành công")
            st.session_state['logged_in'] = True

        username = st.session_state["username"]
        user_role = user_config['usernames'][username].get('role', 'user')
        user_name_display = user_config['usernames'][username]['name']

        with st.sidebar:
            st.write(f'Xin chào, **{user_name_display}**! 👋')
            if user_role == 'admin': st.caption("👑 Quản trị viên")
            else: st.caption("👤 Người dùng")
            
            authenticator.logout('Đăng xuất', 'sidebar')
            st.markdown("---")
        
        st.title("🌐 HỆ THỐNG QUẢN LÝ BHXH")
        df = nap_du_lieu_toi_uu()
        
        if df.empty:
            st.warning("⚠️ Chưa có dữ liệu.")
            if user_role == 'admin':
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
            st.sidebar.button("📝 NHẬT KÝ", on_click=set_state, args=('admin_log',)) # Nút mới
            st.sidebar.button("⚙️ CẬP NHẬT DATA", on_click=set_state, args=('admin_data',))
            st.sidebar.button("👥 QUẢN LÝ USER", on_click=set_state, args=('admin_user',)) # Nút đã sửa

        st.markdown("---")
        for key in ['search', 'loc', 'han', 'bieu', 'ai', 'admin_data', 'admin_user', 'admin_log']:
            if key not in st.session_state: st.session_state[key] = False

        if st.session_state.get('loc'): hien_thi_loc_loi(df, ten_cot)
        elif st.session_state.get('han'): hien_thi_kiem_tra_han(df, ten_cot)
        elif st.session_state.get('bieu'): hien_thi_bieu_do_tuong_tac(df, ten_cot)
        elif st.session_state.get('ai'): hien_thi_chatbot_thong_minh(df)
        elif st.session_state.get('admin_data') and user_role == 'admin': hien_thi_quan_tri_data()
        elif st.session_state.get('admin_user') and user_role == 'admin': hien_thi_quan_ly_user(user_config)
        elif st.session_state.get('admin_log') and user_role == 'admin': hien_thi_nhat_ky_he_thong()
        
        elif tim_kiem:
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