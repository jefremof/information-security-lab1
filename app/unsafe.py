from flask import Flask, request
from template import render_page
from models import db, User, Record
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project.db"
db.init_app(app)

def add_record_unsafe(user_text: str):
    sql_query = f"INSERT INTO record (text) VALUES ('{user_text}')"
    print(sql_query)
    with db.engine.connect() as connection:
        conn = connection.connection
        conn.executescript(sql_query)
        conn.commit()

@app.get('/api/data/')
def get_data():
    all_records = db.session.execute(db.select(Record)).scalars().all()
    record_texts = [record.text for record in all_records]
    return render_page(record_texts)

@app.post('/api/records/')
def insert_record():
    text = request.form['text']
    add_record_unsafe(text)
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