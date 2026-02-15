# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from schemas import RegisterResponse, UserCreate, Token, ChangePassword, ChangePasswordByIdentifier
from crud.user import get_user_by_email, create_user, get_user_by_mobile_number, verify_password, change_password
from crud.salon import list_salons
from app.db.models import Salon
from core.security import create_access_token
from api.deps import get_db, get_current_user

router = APIRouter()


class LoginIn(BaseModel):
    email: str
    password: str

class LoginInWithMobile(BaseModel):
    phone: str
    password: str


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = create_user(db, email=payload.email, password=payload.password,
                       name=payload.name, phone=payload.phone, role=payload.role)
    # return a safe dict (exclude hashed_password) — ensure it matches RegisterResponse.data
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
        "created_at": str(user.created_at) if user.created_at else None,
    }
    return {"status": status.HTTP_200_OK, "data": user_data, "message": "User registered successfully"}


@router.post("/login", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = get_user_by_email(db, payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    # include sanitized user object (without password) inside the token
    access_token = create_access_token(subject=user)
    # Get salon_id using the salon listing approach
    salons = list_salons(db, owner_id=user.id, limit=1)
    salon_id = salons[0].id if salons else None
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
        "salon_id": salon_id,
        "access_token": access_token,
        "token_type": "bearer"
    }
    return {"status": status.HTTP_200_OK, "data": user_data, "message": "Login successful"}

@router.post("/login-with-mobile", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginInWithMobile, db: Session = Depends(get_db)):
    user = get_user_by_mobile_number(db, payload.phone)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    # include sanitized user object (without password) inside the token
    access_token = create_access_token(subject=user)
    # Get salon_id using the salon listing approach
    salons = list_salons(db, owner_id=user.id, limit=1)
    salon_id = salons[0].id if salons else None
    user_data = {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "phone": user.phone,
        "role": user.role,
        "salon_id": salon_id,
        "access_token": access_token,
        "token_type": "bearer"
    }
    return {"status": status.HTTP_200_OK, "data": user_data, "message": "Login successful"}


@router.post("/change-password", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def change_password_endpoint(payload: ChangePassword, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Change the current user's password after verifying the old password."""
    user = change_password(db, current_user, old_password=payload.old_password, new_password=payload.new_password)
    return {"status": status.HTTP_200_OK, "data": {"id": user.id, "email": user.email}, "message": "Password updated successfully"}


@router.post("/change-password/by-identifier", response_model=RegisterResponse, status_code=status.HTTP_200_OK)
def change_password_by_identifier(payload: ChangePasswordByIdentifier, db: Session = Depends(get_db)):
    """Change password by looking up user by email or phone (requires old_password)."""
    user = None
    if payload.email:
        user = get_user_by_email(db, payload.email)
    if not user and payload.phone:
        user = get_user_by_mobile_number(db, payload.phone)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = change_password(db, user, old_password=payload.old_password, new_password=payload.new_password)
    return {"status": status.HTTP_200_OK, "data": {"id": user.id, "email": user.email, "phone": user.phone}, "message": "Password updated successfully"}

