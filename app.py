import base64
import os
from random import randint
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, desc
from chat_agent import init, response
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from voice import trans
import requests
from werkzeug.utils import secure_filename


app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@172.24.167.166:5433/flask"
app.config['SECRET_KEY'] = '06a9fb13c0394bf2966d58a5ebd14f86'
ALGORITHM = "HS256"
db = SQLAlchemy(app)
token = None


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String, nullable = False)
    name = db.Column(db.String, nullable = False)
    password = db.Column(db.String, nullable = False)
    phone_number = db.Column(db.String)
    gender = db.Column(db.String)
    avatar = db.Column(db.String)
    reset_code = db.Column(db.Integer)
    reset_code_exp = db.Column(db.DateTime) 


class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String)
    status = db.Column(db.String)


class Progress(db.Model):
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)
    duration = db.Column(db.Float, nullable=False)
    total_turns = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String, nullable=False)
    vocab = db.Column(db.Integer, nullable=False)
    grammar = db.Column(db.Integer, nullable=False)
    fluency = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.String, nullable=False)
    response_time = db.Column(db.Float, nullable=False)


class Document(db.Model):
    __tablename__ = 'text'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.LargeBinary, nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)


class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    content = db.Column(db.String, nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    
    def __repr__(self):
        return f'{self.content}'


class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    content = db.Column(db.String, nullable=False)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)
    language = db.Column(db.String)

    def __repr__(self):
        return f'{self.content}'


class Question_voice(db.Model):
    __tablename__ = 'question_voice'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.LargeBinary, nullable=False)  # Lưu dạng nhị phân (binary)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)


def token_required(func):
    @wraps(func)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization']
        else:
            return {'message': 'token is missing'}, 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], [ALGORITHM])
        except jwt.PyJWTError:
            return {'message': 'token is invalid'}, 401

        user = User.query.filter(User.id == data['id']).first()
        return func(user, *args, **kwargs)
    return decorated


@app.route('/signup', methods = ['POST'])
def signup():
    email = request.json.get('email')
    name = request.json.get('name')
    password = request.json.get('password')
    phone_number = request.json.get('phone_number')
    gender = request.json.get('gender')
    user = User.query.filter(User.email == email).first()
    avatar = 'static/avatars/default.jpg'

    if not user:
        record = User(email=email, 
                      name=name, 
                      phone_number=phone_number, 
                      gender=gender, 
                      password = generate_password_hash(password),
                      avatar=avatar)
        db.session.add(record)
        db.session.commit()
        return {'message': 'sign up success'}, 201  
    else:
        return {'message': 'user already exists'}, 202


@app.route('/login', methods = ['POST'])
def login():
    if request.method == 'OPTIONS':
        return {'message': 'oke'}, 200
    
    email = request.json.get('email')
    password = request.json.get('password')
    user = User.query.filter(User.email == email).first()

    if not user:
        return {'message': 'user does not exists'}, 401
    
    if check_password_hash(pwhash=user.password, password=password):
        global token
        token = jwt.encode({'id': user.id, 
                            'exp': datetime.now(timezone.utc) + timedelta(minutes=15)}, app.config['SECRET_KEY'], ALGORITHM)
        refresh_token = jwt.encode({
            'id': user.id,
            'exp': datetime.now(timezone.utc) + timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm=ALGORITHM)
        return {'token': token, 'refresh_token': refresh_token}, 201
    else:
        return {'message': 'password is wrong'}, 403


@app.route('/refresh', methods=['POST'])
def refresh():
    refresh_token = request.json.get('refresh_token')
    try:
        data = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=ALGORITHM)
        global token
        token = jwt.encode({
            'id': data['id'],
            'exp': datetime.now(timezone.utc) + timedelta(minutes=15)
        }, app.config['SECRET_KEY'], algorithm=ALGORITHM)
        return {'token': token}, 200
    except jwt.ExpiredSignatureError:
        return {'message': 'Refresh token expired'}, 401
    except jwt.InvalidTokenError:
        return {'message': 'Invalid refresh token'}, 403


@app.route('/documents/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def documents(user, chat_id):
    if request.method == 'GET':
        records = Document.query.filter(Document.chat_id==chat_id).all()
        items = [{'id': record.id, 'content': record.content, 'chat_id': record.chat_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return {'message': 'file not found'}, 404
        file = request.files['file']
        #store_db(file.read().decode('utf-8'))
        new_file = Document(content=file.read(), chat_id=chat_id)
        db.session.add(new_file)
        db.session.commit()
        return {'message': 'upload success'}, 200


@app.route('/chats', methods = ['GET', 'POST', 'DELETE'])
@token_required
def chats(user):
    if request.method == 'GET':
        records = Chat.query.filter(Chat.user_id==user.id).all()
        if not records:
            return {'detail': f'chat with user id {user.id} not found'}, 404
        items = [{'id': record.id, 'time': record.time, 'name': record.name, 'status': record.status, 'user_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        time = datetime.now(timezone.utc) #+ timedelta(hours=7)
        item = Chat(user_id=user.id, time=time, status='start')
        db.session.add(item)
        db.session.commit()
        records = Chat.query.filter(Chat.user_id==user.id).all()
        new_chat = records[-1]
        init(token, new_chat.id)
        return {'content': 'post success', 'new_chat_id': new_chat.id}, 201
    
    if request.method == 'DELETE':
        chats = Chat.query.filter_by(user_id=user.id).all()
        if not chats:
            return {'detail': f'chat with user id {user.id} not found'}, 404
        for chat in chats:
            db.session.delete(chat)
        db.session.commit()
        return {'content': 'All chats deleted successfully for the user'}, 200
 

@app.route('/chats/<int:chat_id>', methods=['PUT', 'DELETE'])
@token_required
def chat(user, chat_id):
    if request.method == 'PUT':
        name = request.json.get('name')
        status = request.json.get('status')
        if name is None:
            return {'detail': 'Missing "name" in request'}, 400
        chat = Chat.query.filter_by(id=chat_id).first()
        if not chat:
            return {'detail': 'Chat not found'}, 404
        chat.name = name
        chat.status = status
        db.session.commit()
        return {'content': 'Chat updated successfully'}, 200
    
    if request.method == 'DELETE':
        chat = Chat.query.filter_by(id=chat_id).first()
        if not chat:
            return {'detail': f'Chat with id {chat_id} not found'}, 404
        db.session.delete(chat)
        db.session.commit()
        return {'content': 'Chat deleted successfully'}, 200


@app.route('/questions/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def questions(user, chat_id):
    if request.method == 'GET':
        records = Question.query.filter(Question.chat_id==chat_id).all()
        if not records:
            return {'detail': f'questions with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'time': record.time, 'chat_id': record.chat_id} for record in records]
        return items, 200

    if request.method == 'POST':
        records = Chat.query.filter(Chat.id==chat_id).all()
        if not records:
            return {'detail': f'chat with id {chat_id} not found'}, 404

        time = datetime.now(timezone.utc) #+ timedelta(hours=7)
        item_content = request.json.get('content')
        item = Question(content=item_content, chat_id = chat_id, time=time)
        db.session.add(item)
        db.session.commit()
        return response(token, item_content, chat_id), 201
        #return {'content': response(token, item_content, chat_id)}, 201


@app.route('/answers/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def answers(user, chat_id):
    if request.method == 'GET':
        records = Answer.query.filter(Answer.chat_id == chat_id).all()
        if not records:
            return {'detail': f'answers with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'time': record.time, 'language': record.language, 'chat_id': record.chat_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        item_content = request.json.get('content')
        item_language = request.json.get('language')
        time = datetime.now(timezone.utc) #+ timedelta(hours=7)
        item = Answer(content=item_content, language=item_language, chat_id = chat_id, time=time)
        db.session.add(item)
        db.session.commit()
        return 'post success', 201


@app.route('/questions_voices/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def questions_voices(user, chat_id):
    if request.method == 'GET':
        records = Question_voice.query.filter(Question_voice.text_id==chat_id).all()
        if not records:
            return {'detail': f'questions voices with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'content': base64.b64encode(record.content).decode('utf-8'), 'text_id': record.chat_id, 'chat_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return {'message': 'file not found'}, 404
        records = Question_voice.query.filter(Question_voice.chat_id==chat_id).first()
        if not records:
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json',
            }
            try:
                response = requests.post(f'http://127.0.0.1:5000/chats', headers=headers)
            except: 
                print(response.status_code)
            print(response)

        file = request.files['file']
        file_bytes = file.read()
        new_file = Question_voice(content=file_bytes, chat_id = chat_id)
        db.session.add(new_file)
        ans = trans(token, file_bytes, file.filename, chat_id)

        time = datetime.now(timezone.utc) #+ timedelta(hours=7)
        item = Question(content=ans["question"], chat_id = chat_id, time=time)
        db.session.add(item)
        db.session.commit()
        return ans, 201


@app.route('/progress/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def progress(user, chat_id):
    if request.method == 'GET':
        records = Progress.query.filter(Progress.chat_id == chat_id).all()
        if not records:
            return {'detail': f'progress with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 
                  'duration': record.duration, 
                  'topic': record.topic, 
                  'total_turns': record.total_turns, 
                  'vocab': record.vocab, 
                  'grammar': record.grammar, 
                  'fluency': record.fluency, 
                  'feedback': record.feedback, 
                  'response_time': record.response_time,
                  'chat_id': record.chat_id} for record in records]
        return items, 200

    if request.method == 'POST':
        start = Question.query.filter(Question.chat_id == chat_id).order_by(asc(Question.time)).first()
        end = Question.query.filter(Question.chat_id == chat_id).order_by(desc(Question.time)).first()
        duration = end.time - start.time
        duration = round(duration.total_seconds() / 60, 2)

        topic = request.json.get('topic')
        vocab = request.json.get('vocab')
        grammar = request.json.get('grammar')
        fluency = request.json.get('fluency')
        feedback = request.json.get('feedback')
        total_turns = Question.query.filter(Question.chat_id == chat_id).count()
        response_time = duration/total_turns
        item = Progress(duration=duration, 
                        topic=topic, 
                        total_turns=total_turns, 
                        vocab=vocab, 
                        grammar=grammar, 
                        fluency=fluency, 
                        feedback=feedback, 
                        response_time=response_time,
                        chat_id=chat_id)
        db.session.add(item)
        db.session.commit()
        return 'post success', 201


UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/users', methods = ['GET', 'PUT'])
@token_required
def users(user):
    if request.method == 'GET':
        record = User.query.filter(User.id == user.id).first()
        if not record:
            return {'detail': f'user with user id {user.id} not found'}, 404
        item = {'id': record.id, 
                'email': record.email, 
                'name': record.name, 
                'password': record.password, 
                'phone_number': record.phone_number, 
                'gender': record.gender,
                'avatar': record.avatar}
        return item, 200
    
    if request.method == 'PUT':
        record = User.query.filter(User.id == user.id).first()
        record.name = request.json.get('name')
        record.phone_number = request.json.get('phone_number')
        record.gender = request.json.get('gender')
        db.session.commit()
        return 'update user success', 201


@app.route('/avatars', methods = ['PUT'])
@token_required
def avatars(user):
    if request.method == 'PUT':
        record = User.query.filter(User.id == user.id).first()
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                record.avatar = filepath
        db.session.commit()
        return 'update avatar success', 201


from flask_mail import Mail, Message
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'phannthanh2005@gmail.com'        # tài khoản Gmail
app.config['MAIL_PASSWORD'] = 'sinv pryq optg oiyy'      # mật khẩu ứng dụng
mail = Mail(app)


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    if not user:
        return {'message': 'Email not found'}, 404
    otp = str(randint(100000, 999999)) 
    user.reset_code = otp
    user.reset_code_exp = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.session.commit()

    msg = Message(
        subject='Your OTP to reset password',
        sender=app.config['MAIL_USERNAME'],
        recipients=[email],
        body=f'Your OTP is: {otp}. It will expire in 10 minutes.'
    )
    mail.send(msg)
    return {'message': 'OTP sent to your email'}, 200


@app.route('/reset_password', methods=['POST'])
def reset_password():
    email = request.json.get('email')
    otp = request.json.get('otp')
    new_password = request.json.get('new_password')
    user = User.query.filter_by(email=email).first()
    exp = (user.reset_code_exp).replace(tzinfo=timezone.utc)
    if not user:
        return {'message': 'Email not found'}, 404
    if user.reset_code != otp or exp < datetime.now(timezone.utc):
        return {'message': 'Invalid or expired OTP'}, 400

    user.password = generate_password_hash(new_password)
    user.reset_code = None
    user.reset_code_exp = None
    db.session.commit()
    return {'message': 'Password reset successful'}, 200


@app.route('/')
def index():
    return 'hello world', 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)
