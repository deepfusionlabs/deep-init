from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.service import register_user, login_user

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return register_user(db, req.email, req.password, req.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    try:
        return login_user(db, req.email, req.password)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
