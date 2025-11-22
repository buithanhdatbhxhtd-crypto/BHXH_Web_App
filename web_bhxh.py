import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import bcrypt  # <--- Thêm thư viện này để tạo mã hash trực tiếp

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="BHXH Web Manager", layout="wide")

def main():
    # =====================================================
    # BƯỚC 1: LẤY MÃ HASH (Dùng bcrypt trực tiếp - Ổn định hơn)
    # =====================================================
    st.header("🛠️ Công cụ tạo mã Hash mật khẩu")
    st.info("Hãy copy chuỗi ký tự bắt đầu bằng $2b$... bên dưới và dán vào file config.yaml")
    
    try:
        # Mật khẩu cần tạo mã
        mat_khau = "12345"
        
        # Tạo mã hash trực tiếp bằng bcrypt
        hashed_bytes = bcrypt.hashpw(mat_khau.encode(), bcrypt.gensalt())
        hashed_string = hashed_bytes.decode()
        
        st.code(hashed_string, language='text')
    except Exception as e:
        st.error(f"Có lỗi khi tạo hash: {e}")

    st.markdown("---")
    # =====================================================

    st.write("Sau khi bạn copy mã trên và cập nhật vào file config.yaml, chúng ta sẽ xóa đoạn code tạo mã này đi.")

if __name__ == "__main__":
    main()