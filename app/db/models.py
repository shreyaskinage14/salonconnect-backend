# app/db/models.py
from sqlalchemy import Column, Integer, String, DateTime, func, ForeignKey, Float, Text, Boolean,Enum
from sqlalchemy.orm import relationship
from app.db.session import Base
import enum


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="customer")  # customer | barber | admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Salon(Base):
    __tablename__ = "salons"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    business_name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    address = Column(String, nullable=True)
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    city = Column(String, nullable=True)
    # New fields for timezone and working hours (simple per-day range)
    # e.g. "Asia/Kolkata"
    timezone = Column(String, nullable=False, default="UTC")
    # hour in 24h (local salon tz)
    work_start_hour = Column(Integer, nullable=False, default=9)
    # hour in 24h (local salon tz)
    work_end_hour = Column(Integer, nullable=False, default=18)

    owner = relationship("User", backref="salons")
    services = relationship(
        "Service", back_populates="salon", cascade="all, delete-orphan")
    employees = relationship("Employee", back_populates="salon")



class Service(Base):
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, nullable=False, default=30)
    price = Column(Float, nullable=False, default=0.0)

    salon = relationship("Salon", back_populates="services")

    employees = relationship("Employee", back_populates="service")



class BookingStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"
    completed = "completed"


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False)  # customer
    # ISO timestamp expected
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False,
                    default=BookingStatus.pending.value)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    salon = relationship("Salon", backref="bookings")
    service = relationship("Service")
    user = relationship("User")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    experience_years = Column(Integer, nullable=False)
    phone = Column(String, nullable=True)

    salon_id = Column(Integer, ForeignKey("salons.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)

    is_active = Column(Boolean, default=True)

    salon = relationship("Salon", back_populates="employees")
    service = relationship("Service", back_populates="employees")
