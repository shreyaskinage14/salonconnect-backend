# app/schemas.py
from pydantic import BaseModel, EmailStr, root_validator
from typing import Optional, List
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[int] = None  # e.g., 0=admin,1=customer,2=salon_owner


class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[int] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    phone: Optional[str] = None
    role: str  # DB stores as string mostly, or mapped. User model has default="customer"
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class ChangePasswordByIdentifier(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    old_password: str
    new_password: str

    def require_email_or_phone(cls, values):
        if not values.get("email") and not values.get("phone"):
            raise ValueError("Either email or phone is required")
        return values

class RegisterResponse(BaseModel):
    status: int
    message: str
    data: dict

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Salon / Service schemas ---


class ServiceCreate(BaseModel):
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None


class ServiceOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    duration_minutes: int
    price: float

    class Config:
        orm_mode = True


class SalonCreate(BaseModel):
    business_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    timezone: Optional[str] = "UTC"
    work_start_hour: Optional[int] = 9
    work_end_hour: Optional[int] = 18
    services: Optional[List[ServiceCreate]] = []
    city: Optional[str] = None
    owner_details: Optional[UserCreate] = None

class SalonOut(BaseModel):
    id: int
    owner_id: int
    business_name: str
    description: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    phone: Optional[str] = None
    timezone: str
    work_start_hour: int
    work_end_hour: int
    created_at: Optional[str] = None  # ISO format datetime string
    city: Optional[str] = None
    services: List[ServiceOut] = []

    class Config:
        orm_mode = True


# bookings schemas (add to app/schemas.py)

class BookingCreate(BaseModel):
    salon_id: int
    service_id: int
    start_time: datetime  # ISO format accepted
    # end_time optional if you want to compute from service duration; include for flexibility:
    end_time: Optional[datetime] = None


class BookingOut(BaseModel):
    id: int
    salon_id: int
    service_id: int
    user_id: int
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


class EmployeeCreate(BaseModel):
    name: str
    experience_years: int
    service_id: int

    salon_id: Optional[int] = None
    phone: Optional[str] = None

class EmployeeResponse(BaseModel):
    id: int
    name: str
    experience_years: int
    service_id: int
    phone: Optional[str] = None
    salon_id: int
    is_active: bool

    class Config:
        orm_mode = True
