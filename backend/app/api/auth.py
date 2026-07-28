from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from backend.app.db.database import get_session
from backend.app.models.user import User
from backend.app.core.security import hash_password, verify_password
from backend.app.core.jwt_handler import create_access_token, create_refresh_token, decode_token
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["auth"])

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/signup")
def signup(data: SignupRequest, session: Session = Depends(get_session)):
    existing_user = session.exec(select(User).where(User.email == data.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password)
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return {"message": "User created successfully", "user_id": user.id}

@router.post("/login")
def login(data: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == data.email)).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/refresh")
def refresh(data: RefreshRequest):
    try:
        payload = decode_token(data.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    new_access_token = create_access_token({"sub": payload["sub"]})
    return {"access_token": new_access_token, "token_type": "bearer"}