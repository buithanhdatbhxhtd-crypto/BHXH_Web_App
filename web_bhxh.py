import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide")

def main():
    # =====================================================
    # BƯỚC 1: LẤY MÃ HASH (Đoạn code tạm thời)
    # =====================================================
    st.header("🛠️ Công cụ tạo mã Hash mật khẩu")
    st.info("Hãy copy chuỗi ký tự bên dưới và dán vào file config.yaml, sau đó xóa đoạn code này đi.")
    
    # Tạo mã hash cho mật khẩu "12345"
    passwords_to_hash = ['12345']
    
    # Lưu ý: Cú pháp này dành cho streamlit-authenticator phiên bản mới
    try:
        hashed_passwords = stauth.Hasher(passwords_to_hash).generate()
        st.code(hashed_passwords[0], language='text')
    except Exception as e:
        st.error(f"Có lỗi khi tạo hash: {e}")

    st.markdown("---")
    # =====================================================

    # --- PHẦN CÒN LẠI CỦA ỨNG DỤNG (Sẽ chạy sau khi có config đúng) ---
    st.write("Sau khi cập nhật file config.yaml với mã hash trên, ứng dụng sẽ hiển thị màn hình đăng nhập tại đây.")

if __name__ == "__main__":
    main()