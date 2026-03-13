import sqlite3
import os
from passlib.context import CryptContext

# Security: Password hashing setup
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def init_user_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_user(name, email, password):
    hashed_pwd = get_password_hash(password)
    avatar = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=random&color=fff"
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password, avatar) VALUES (?, ?, ?, ?)",
            (name, email, hashed_pwd, avatar)
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"id": user_id, "name": name, "email": email, "avatar": avatar}
    except sqlite3.IntegrityError:
        return None  # Email already exists

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user["password"]):
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "avatar": user["avatar"]
        }
    return None
