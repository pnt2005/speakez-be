## Hướng dẫn chạy ứng dụng

# Bước 1: Tạo và kích hoạt virtual environment (venv)
## Tạo virtual environment
python -m venv venv
### hoặc
python3 -m venv venv
## Kích hoạt venv

### Trên Windows
venv\Scripts\activate

# Bước 2: Cài đặt các thư viện cần thiết
pip install -r requirements.txt

# Bước 3: Chạy ứng dụng
python app.py

# Lưu ý: cần tạo các biến sau
OPENAI_API_KEY, DATABASE_URL, SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD
