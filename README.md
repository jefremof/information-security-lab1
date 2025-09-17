# Информационная безопасность. Лабораторная работа 1

## Запуск

### Запуск проекта:
```shell
pip install -r requirements.txt
```

Версия с исправленными уязвимостями:
```shell
SECRET_KEY="..." DEFAULT_USERNAME="..." DEFAULT_PASSWORD="..." python3 app/safe.py
```

Версия с присутствующими уязвимостями:
```shell
SECRET_KEY="..." DEFAULT_USERNAME="..." DEFAULT_PASSWORD="..." python3 app/unsafe.py
```

`DEFAULT_USERNAME` – содержит логин для тестовой записи пользователя.\
`DEFAULT_PASSWORD` – содержит пароль для тестовой записи пользователя.\
При инициализации Flask приложения автоматически создается тестовый пользователь.

`SECRET_KEY` – используется для шифрования JWT-токенов.

### Запуск сканеров: (локально)

**Bandit**
```shell
bandit -r app/ --exclude unsafe.py
```

**Snyk**
```shell
snyk ignore --file-path=app/unsafe.py
snyk code test
```


## Обзор

Структура проекта:
- requirements.txt  – зависимости
- app\
    - models.py     – модели (`User`, `Record`)
    - template.py   – шаблон для HTML страницы 
    - safe.py       - Flask приложение с исправленными уязвимостями
    - unsafe.py     - Flask приложение с наличием уязвимостей

Проект содержит следующие эндпоинты:

- `/auth/login` (POST)\
    В теле запроса следует передавать JSON с логином и паролем:
    ```json
    {"username":"testuser", "password":"secure"}
    ```

    Возвращает JWT-токен.

- `/api/data/` (GET)\
    Требует JWT-токена: `Authorization: Bearer <Token>`

    Возвращает HTML страницу, отображающую список текстовых записей (поля text для всех элементов Record).

- `/api/records/` (POST)\
    Требует JWT-токена: `Authorization: Bearer <Token>`

    В теле запроса в form-data необходимо передать:
    `text: <Текст>`

    Добавляет текстовую запись с переданным содержанием.


## Меры защиты

### SQL Injection

**Неправильная реализация:**\
Выполняет "сырой" SQL запрос.
```python
def add_record_unsafe(user_text: str):
    sql_query = f"INSERT INTO record (text) VALUES ('{user_text}')"
    print(sql_query)
    with db.engine.connect() as connection:
        conn = connection.connection
        conn.executescript(sql_query)
        conn.commit()
```

**Исправление:**\
Выполняется запрос через ORM.\
ORM по умолчанию предоставляет защиту от SQLi.\
Даже выполнение `session.execute(text(<RAW SQL>))` не приведет к SQLi, поскольку этот метод следит за тем, чтобы выполнялся только один запрос.
```python
def add_record_safe(user_text: str):
    try:
        new_record = Record(text=user_text)
        db.session.add(new_record)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
```

### XSS

**Неправильная реализация:**
```python
@app.post('/api/records/')
def insert_record():
    text = request.form['text']
    add_record_unsafe(text)
    return {"text": text}
```

**Исправление:**\
Используется встроенное средство `escape` из модуля markupsafe, который предоставляется вместе с шаблонизатором Jinja2. 
```python
@app.post('/api/records/')
@jwt_required
def insert_record():
    text = escape(request.form['text'])
    add_record_safe(text)
    return {"text": text}
```

### Аутентификация

Используется PyJWT для проверки и формирования токенов.

Эндпоинт `auth/login/` сверяет переданные логин и пароль с хранящимися в базе данных, формирует токен и отправляет его в ответе.
```python
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
```

Middleware реализован в виде декоратора, который извлекает токен из заголовка, проверяет его корректность, и переходит к выполнению обработчика запроса, если всё в порядке.
```python
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
```

## Демонстрация

### Уязвимости (`unsafe.py`)

1. Получение данных без аутентификации (`/api/data/`)

2. Вставка несанитизированных пользовательских данных. Неэкранированный HTML с JS скриптом. (`/api/records/`)

Приводит к выполнению вредоносного javascript кода на странице в браузере пользователя.

3. SQL инъекция. Выполнение сырого SQL запроса. (`/api/records/`)

Приводит к несанкционированному доступу к конфиденциальным данным.


### Проверка кода с уязвимостями с помощью сканнеров

1. Bandit выявил только SQL Injection

2. Snyk также выявил только SQL Injection


### Код без уязвимостей (`safe.py`)

1. Нельзя получить данные без аутентификации (`/api/data/`)
2. Токен нельзя получить, указав неправильный пароль (`/auth/login/`)
3. Получение токена (`/auth/login/`)
4. SQLi и XSS не работают:
SQL и HTML экранируются

### Скриншоты отчетов SAST/SCA

SAST

SCA