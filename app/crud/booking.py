# app/crud/booking.py
from sqlalchemy.orm import Session
from app.db import models
from datetime import datetime, timedelta
from typing import List, Optional


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


def create_booking(db: Session, user_id: int, salon_id: int, service_id: int, start_time: datetime, end_time: datetime) -> models.Booking:
    # Check service belongs to salon
    svc = db.query(models.Service).filter(models.Service.id ==
                                          service_id, models.Service.salon_id == salon_id).first()
    if not svc:
        raise ValueError("Service not found for this salon")

    # Check overlapping bookings for the same service (approved or pending)
    existing = db.query(models.Booking).filter(
        models.Booking.service_id == service_id,
        models.Booking.status.in_(
            [models.BookingStatus.pending.value, models.BookingStatus.approved.value])
    ).all()

    for b in existing:
        if _overlaps(start_time, end_time, b.start_time, b.end_time):
            raise ValueError("Requested slot overlaps an existing booking")

    booking = models.Booking(
        salon_id=salon_id,
        service_id=service_id,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        status=models.BookingStatus.pending.value
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def get_booking(db: Session, booking_id: int) -> Optional[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.id == booking_id).first()


def list_user_bookings(db: Session, user_id: int) -> List[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.user_id == user_id).order_by(models.Booking.created_at.desc()).all()


def list_salon_bookings(db: Session, salon_id: int) -> List[models.Booking]:
    return db.query(models.Booking).filter(models.Booking.salon_id == salon_id).order_by(models.Booking.start_time.desc()).all()


def update_booking_status(db: Session, booking: models.Booking, new_status: str):
    booking.status = new_status
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def delete_booking(db: Session, booking: models.Booking):
    db.delete(booking)
    db.commit()
