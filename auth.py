from passlib.hash import bcrypt
from datetime import datetime, timedelta
import jwt
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

def hash_password(password: str):
    """Hash a password using bcrypt"""
    # Truncate to 72 characters (bcrypt limitation)
    if len(password) > 72:
        password = password[:72]
    return bcrypt.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    """Verify a password against a hash"""
    if len(plain_password) > 72:
        plain_password = plain_password[:72]
    return bcrypt.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    """Create JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str):
    """Decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None