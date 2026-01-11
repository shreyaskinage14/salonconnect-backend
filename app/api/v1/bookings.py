# app/api/v1/bookings.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from crud.booking import create_booking, get_booking, list_user_bookings, list_salon_bookings, update_booking_status, delete_booking
from schemas import BookingCreate, BookingOut
from app.db import models
from api.deps import get_db, get_current_user

router = APIRouter()


# Helper: convert Booking ORM -> plain dict (safe across Pydantic versions)
def _booking_to_dict(b):
    return {
        "id": b.id,
        "salon_id": b.salon_id,
        "service_id": b.service_id,
        "user_id": b.user_id,
        "start_time": b.start_time.isoformat() if b.start_time is not None else None,
        "end_time": b.end_time.isoformat() if b.end_time is not None else None,
        "status": b.status,
        "created_at": b.created_at.isoformat() if b.created_at is not None else None,
    }


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(
    payload: BookingCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new booking. Requires authentication."""
    # compute end_time if missing using service duration
    svc = db.query(models.Service).filter(
        models.Service.id == payload.service_id).first()
    if not svc:
        raise HTTPException(status_code=404, detail="Service not found")
    start = payload.start_time
    end = payload.end_time or (start + timedelta(minutes=svc.duration_minutes))
    try:
        booking = create_booking(db, user_id=current_user.id, salon_id=payload.salon_id,
                                 service_id=payload.service_id, start_time=start, end_time=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _booking_to_dict(booking)


@router.get("", response_model=list[BookingOut])
def list_my_bookings(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List current user's bookings. Requires authentication."""
    return [_booking_to_dict(b) for b in list_user_bookings(db, current_user.id)]


@router.get("/salon/{salon_id}", response_model=list[BookingOut])
def list_bookings_for_salon(
    salon_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List bookings for a salon. Only salon owner or admin can view."""
    # only salon owner or admin can view
    salon = db.query(models.Salon).filter(models.Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    if salon.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return [_booking_to_dict(b) for b in list_salon_bookings(db, salon_id)]


@router.patch("/{booking_id}", response_model=BookingOut)
def update_booking(
    booking_id: int,
    action: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    action (query param): 'approve' | 'reject' | 'cancel' | 'complete'
      - approve/reject: salon owner (or admin)
      - cancel: customer who created it (or admin)
      - complete: salon owner (or admin)
    """
    user = current_user
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    # Helper permission checks
    is_owner = booking.salon.owner_id == user.id
    is_customer = booking.user_id == user.id
    is_admin = user.role == "admin"

    # APPROVE: check owner/admin and overlapping approved bookings
    if action == "approve":
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to approve")
        # re-check overlapping against other APPROVED bookings for same service
        overlaps = db.query(models.Booking).filter(
            models.Booking.service_id == booking.service_id,
            models.Booking.id != booking.id,
            models.Booking.status == models.BookingStatus.approved.value,
        ).all()

        for b in overlaps:
            # simple overlap logic
            if not (booking.end_time <= b.start_time or booking.start_time >= b.end_time):
                raise HTTPException(
                    status_code=400, detail="Cannot approve: overlaps an existing approved booking")

        updated = update_booking_status(
            db, booking, models.BookingStatus.approved.value)
        return _booking_to_dict(updated)

    # REJECT: owner or admin
    if action == "reject":
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to reject")
        updated = update_booking_status(
            db, booking, models.BookingStatus.rejected.value)
        return _booking_to_dict(updated)

    # CANCEL: customer who created it or admin
    if action == "cancel":
        if not (is_customer or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to cancel")
        updated = update_booking_status(
            db, booking, models.BookingStatus.cancelled.value)
        return _booking_to_dict(updated)

    # COMPLETE: owner or admin
    if action == "complete":
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=403, detail="Not authorized to complete")
        updated = update_booking_status(
            db, booking, models.BookingStatus.completed.value)
        return _booking_to_dict(updated)

    raise HTTPException(status_code=400, detail="Invalid action")


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking_endpoint(
    booking_id: int,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a booking. Only the booking owner or admin can delete."""
    booking = get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete")
    delete_booking(db, booking)
    return None

