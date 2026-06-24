from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.auth.models import User
import uuid

SECRET_KEY = "dev-secret-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# BR: Password hashed with bcrypt
# BR: Email must be unique
# BR: JWT expires after 24 hours
def register_user(db: Session, email: str, password: str, name: str) -> dict:
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise ValueError("Email already registered")
    user = User(id=str(uuid.uuid4()), email=email, hashed_password=pwd_context.hash(password), name=name)
    db.add(user)
    db.commit()
    return {"user": {"id": user.id, "email": user.email}, "token": _create_token(user.id)}

# WF: Login — find user → verify password → create JWT
def login_user(db: Session, email: str, password: str) -> dict:
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        raise ValueError("Invalid credentials")
    return {"user": {"id": user.id, "email": user.email}, "token": _create_token(user.id)}

def _create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)
