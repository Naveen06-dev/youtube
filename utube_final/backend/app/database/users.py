import os
from passlib.context import CryptContext
from pymongo import MongoClient
import uuid
from dotenv import load_dotenv

load_dotenv(override=True)

# Security: Password hashing setup
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

MONGO_URI = os.getenv("MONGO_URI")

def get_db():
    try:
        if not MONGO_URI or "<db_password>" in MONGO_URI:
            raise Exception("MONGO_URI environment variable is missing or invalid. Set it in your .env file or hosting provider's environment settings.")
        client = MongoClient(MONGO_URI)
        return client["Naveenutube"]
    except Exception as e:
        print(f"MongoDB Users Error: {e}")
        return None

def init_user_db():
    """MongoDB collections are created automatically upon first insert."""
    pass

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_user(name, email, password):
    db = get_db()
    if db is None:
        raise Exception("Database connection failed. Please check your credentials and Atlas IP Whitelist (0.0.0.0/0).")
        
    users_collection = db.users
    
    # Check if email exists
    if users_collection.find_one({"email": email}):
        return None  # Email actually already exists
        
    hashed_pwd = get_password_hash(password)
    avatar = f"https://ui-avatars.com/api/?name={name.replace(' ', '+')}&background=random&color=fff"
    
    # Generate random unique string ID (similar to what SQLite auto-increment does)
    user_id = str(uuid.uuid4())
    
    user_doc = {
        "_id": user_id,
        "name": name,
        "email": email,
        "password": hashed_pwd,
        "avatar": avatar
    }
    
    users_collection.insert_one(user_doc)
    
    return {"id": user_id, "name": name, "email": email, "avatar": avatar}

def authenticate_user(email, password):
    db = get_db()
    if db is None:
        return None
        
    users_collection = db.users
    user = users_collection.find_one({"email": email})
    
    if user and verify_password(password, user["password"]):
        return {
            "id": str(user["_id"]),
            "name": user["name"],
            "email": user["email"],
            "avatar": user["avatar"]
        }
    return None
