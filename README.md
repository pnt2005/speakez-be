## Ứng dụng giúp người dùng luyện tập hội thoại bằng ngoại ngữ thông qua trò chuyện với chatbot.
## Tính năng:
- Chatbot phản hồi theo ngữ cảnh
- Phân tích độ phản xạ và gợi ý luyện tập
- Ghi nhận kết quả và hiển thị tiến trình học
## front end: https://github.com/ngodinhan058/ProjectMobileFE_ADVEN
## demo: 
- https://drive.google.com/file/d/1c02e_SCTNiA4dNCtr2qrjohC-cpZxUZQ/view
- https://drive.google.com/file/d/1tKLi5f2kKwnkvUFv1zgfq5yfsF90X7vK/view
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
