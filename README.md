## Application for Practicing Foreign Language Conversations with a Chatbot
## Features:
- Contextual chatbot responses
- Analysis of reaction speed and practice suggestions
- Tracking results and displaying learning progress
## front end: https://github.com/ngodinhan058/ProjectMobileFE_ADVEN
## demo: 
- [https://drive.google.com/file/d/1c02e_SCTNiA4dNCtr2qrjohC-cpZxUZQ/view](https://docs.google.com/file/d/14MGkwFVHO9Xa5DNlk7xAMiRMpMLSE7JW/preview)
## How to Run the Application

# Step 1: Create and activate a virtual environment (venv)
## Create virtual environment
python -m venv venv
### or
python3 -m venv venv
## Activate venv

### On Windows:
venv\Scripts\activate

# Step 2: Install required libraries
pip install -r requirements.txt

# Step 3: Run the application
python app.py

# Note: You need to set the following environment variables:
OPENAI_API_KEY, DATABASE_URL, SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD
