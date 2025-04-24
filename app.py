import base64
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import asc, desc
from chat_agent import response
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from voice import trans
import requests


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


class Chat(db.Model):
    __tablename__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)


class Progress(db.Model):
    __tablename__ = 'progress'
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey('chat.id', ondelete = "CASCADE"), nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    total_turns = db.Column(db.Integer, nullable=False)
    topic = db.Column(db.String, nullable=False)
    vocab = db.Column(db.Integer, nullable=False)
    grammar = db.Column(db.Integer, nullable=False)


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

    if not user:
        record = User(email=email, name=name, phone_number=phone_number, gender=gender, password = generate_password_hash(password))
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
                            'exp': datetime.now(timezone.utc) + timedelta(hours=3000)}, app.config['SECRET_KEY'], ALGORITHM)
        return {'token': token}, 201
    else:
        return {'message': 'password is wrong'}, 403


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


@app.route('/chats', methods = ['GET', 'POST'])
@token_required
def chats(user):
    if request.method == 'GET':
        records = Chat.query.filter(Chat.user_id==user.id).all()
        if not records:
            return {'detail': f'chat with user id {user.id} not found'}, 404
        items = [{'id': record.id, 'time': record.time, 'user_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        time = datetime.now(timezone.utc) + timedelta(hours=7)
        item = Chat(user_id=user.id, time=time)
        db.session.add(item)
        db.session.commit()
        return {'content': 'post success'}, 201


@app.route('/questions/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def questions(user, chat_id):
    if request.method == 'GET':
        records = Question.query.filter(Question.chat_id==chat_id).all()
        if not records:
            return {'detail': f'questions with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'chat_id': record.chat_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        records = Question.query.filter(Question.chat_id==chat_id).first()
        if not records:
            headers = {
                'Authorization': token,
                'Content-Type': 'application/json',
            }
            try:
                chats_response = requests.post(f'http://127.0.0.1:5000/chats', headers=headers)
            except: 
                print(chats_response.status_code)
            print(chats_response)

        time = datetime.now(timezone.utc) + timedelta(hours=7)
        item_content = request.json.get('content')
        item = Question(content=item_content, chat_id = chat_id, time=time)
        db.session.add(item)
        db.session.commit()
        return {'content': response(token, item_content, chat_id)}, 201


@app.route('/answers/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def answers(user, chat_id):
    if request.method == 'GET':
        records = Answer.query.filter(Answer.chat_id == chat_id).all()
        if not records:
            return {'detail': f'answers with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'chat_id': record.chat_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        item_content = request.json.get('content')
        time = datetime.now(timezone.utc) + timedelta(hours=7)
        item = Answer(content=item_content, chat_id = chat_id, time=time)
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
        db.session.commit()
        ans = trans(token, file_bytes, file.filename, chat_id)
        return {'content': ans}, 201


@app.route('/progress/<int:chat_id>', methods = ['GET', 'POST'])
@token_required
def progress(user, chat_id):
    if request.method == 'GET':
        records = Progress.query.filter(Progress.chat_id == chat_id).all()
        if not records:
            return {'detail': f'progress with chat id {chat_id} not found'}, 404
        items = [{'id': record.id, 'duration': record.duration, 'topic': record.topic, 'total_turns': record.total_turns, 'chat_id': record.chat_id} for record in records]
        return items, 200

    if request.method == 'POST':
        start = Question.query.filter(Question.chat_id == chat_id).order_by(asc(Question.time)).first()
        end = Question.query.filter(Question.chat_id == chat_id).order_by(desc(Question.time)).first()
        duration = end.time - start.time

        topic = request.json.get('topic')
        vocab = request.json.get('vocab')
        grammar = request.json.get('grammar')
        total_turns = Question.query.filter(Question.chat_id == chat_id).count()
        item = Progress(duration=duration, topic=topic, total_turns=total_turns, vocab=vocab, grammar=grammar, chat_id=chat_id)
        db.session.add(item)
        db.session.commit()
        return 'post success', 201


@app.route('/')
def index():
    return 'hello world', 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        app.run(debug=True)
