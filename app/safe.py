from flask import Flask, request, jsonify
from template import render_page
from models import db, User, Record
from markupsafe import escape
from functools import wraps
import datetime
import jwt
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
db.init_app(app)

JWT_EXPIRATION_MIN = 5

def add_record_safe(user_text: str):
    try:
        new_record = Record(text=user_text)
        db.session.add(new_record)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({"msg": "Token is missing!"}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.session.get(User, data['user_id'])
            if current_user is None:
                return jsonify({"msg": "User not found"}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({"msg": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"msg": "Token is invalid"}), 401

        return f(*args, **kwargs)

    return decorated_function

@app.post('/auth/login/')
def login():
    if request.json is None:
        return jsonify({"msg": "Missing body"}), 400
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    user = User.query.filter_by(username=username).first()

    if user is None or not user.check_password(password):
        return jsonify({"msg": "Bad username or password"}), 401

    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=JWT_EXPIRATION_MIN)
    access_token = jwt.encode(
        {"user_id": user.id, "exp": expires},
        app.config['SECRET_KEY'],
        algorithm="HS256"
    )
    return jsonify(access_token=access_token)

@app.get('/api/data/')
@jwt_required
def get_data():
    all_records = db.session.execute(db.select(Record)).scalars().all()
    record_texts = [escape(record.text) for record in all_records]
    return render_page(record_texts)

@app.post('/api/records/')
@jwt_required
def insert_record():
    text = escape(request.form['text'])
    add_record_safe(text)
    return {"text": text}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Set up default user for testing purposes
        default_username = os.getenv("DEFAULT_USERNAME")
        if default_username is not None:
            default_user = User.query.filter_by(username=default_username).first()
            default_password = os.getenv("DEFAULT_PASSWORD")
            if not default_user and default_password is not None:
                default_user = User(username=default_username)
                default_user.set_password(default_password)
                db.session.add(default_user)
                print(f"Added default user")
                db.session.commit()
    
    app.run()