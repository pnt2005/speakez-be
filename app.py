from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from aplpha import response, set_jwt_token#, store_db
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@172.24.167.166:5433/flask"
app.config['SECRET_KEY'] = '06a9fb13c0394bf2966d58a5ebd14f86'
ALGORITHM = "HS256"
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key = True)
    email = db.Column(db.String, nullable = False)
    name = db.Column(db.String, nullable = False)
    password = db.Column(db.String, nullable = False)


class Text(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.LargeBinary, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)


class Question(db.Model):
    __tablename__ = 'question'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    content = db.Column(db.String, nullable=False)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id', ondelete = "CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)
    
    def __repr__(self):
        return f'{self.content}'
    

class Answer(db.Model):
    __tablename__ = 'answer'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    content = db.Column(db.String, nullable=False)
    text_id = db.Column(db.Integer, db.ForeignKey('text.id', ondelete = "CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete = "CASCADE"), nullable=False)

    def __repr__(self):
        return f'{self.content}'

    
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
    user = User.query.filter(User.email == email).first()

    if not user:
        record = User(email = email, name = name, password = generate_password_hash(password))
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
        token = jwt.encode({'id': user.id, 
                            'exp': datetime.utcnow() + timedelta(hours=30)}, app.config['SECRET_KEY'], ALGORITHM)
        set_jwt_token(token)
        return {'token': token}, 201
    else:
        return {'message': 'password is wrong'}, 403
    

@app.route('/texts', methods = ['GET', 'POST'])
@token_required
def text(user):
    if request.method == 'GET':
        records = Text.query.filter(Text.user_id==user.id).all()
        items = [{'id': record.id, 'content': record.content, 'user_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        if 'file' not in request.files:
            return {'message': 'file not found'}, 404
        file = request.files['file']
        #store_db(file.read().decode('utf-8'))
        new_file = Text(content=file.read(), user_id=user.id)
        db.session.add(new_file)
        db.session.commit()
        return {'message': 'upload success'}, 200


@app.route('/texts/<int:id>', methods = ['GET'])
@token_required
def retrieve_text(user, id):
    record = Text.query.filter(Text.id == id, Text.user_id==user.id).first()
    if not record:
        return {'detail': f'text with id {id} not found'}, 404
    item = {'id': record.id, 'content': record.content, 'user_id': record.user_id}
    return item, 200


# @app.route('/upload', methods=['GET','POST'])
# @token_required
# def upload_file(user):
#      if request.method == 'POST':
#         if 'file' not in request.files:
#             return {'message': 'file not found'}, 404
#         file = request.files['file']
#         store_db(file.read().decode('utf-8'))
#         #new_file = File(name=file.name, content=file.read())
#         #db.session.add(new_file)
#         #db.session.commit()
#         return {'message': 'upload success'}, 200


@app.route('/questions/<int:text_id>', methods = ['GET', 'POST'])
@token_required
def question(user, text_id):
    if request.method == 'GET':
        records = Question.query.filter(Question.text_id==text_id, Question.user_id==user.id).all()
        if not records:
            return {'detail': f'questions with text id {text_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'text_id': record.text_id, 'user_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        item_content = request.json.get('content')
        item = Question(content=item_content, text_id = text_id, user_id=user.id)
        db.session.add(item)
        db.session.commit()
        return {'content': response(item_content, text_id)}, 201


@app.route('/answers/<int:text_id>', methods = ['GET', 'POST'])
@token_required
def answer(user, text_id):
    if request.method == 'GET':
        records = Answer.query.filter(Answer.text_id == text_id, Answer.user_id==user.id).all()
        if not records:
            return {'detail': f'answers with text id {text_id} not found'}, 404
        items = [{'id': record.id, 'content': record.content, 'text_id': record.text_id, 'user_id': record.user_id} for record in records]
        return items, 200
    
    if request.method == 'POST':
        item_content = request.json.get('content')
        item = Answer(content=item_content, text_id = text_id, user_id=user.id)
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
