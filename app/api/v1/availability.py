# app/api/v1/availability.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, time, timedelta, date, timezone
from zoneinfo import ZoneInfo

from app.db import models
from app.api.deps import get_db, get_current_user

router = APIRouter()


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return not (a_end <= b_start or a_start >= b_end)


@router.get("/salon/{salon_id}", response_model=List[dict])
def get_availability_for_salon(
    salon_id: int,
    service_id: int = Query(..., description="ID of the service to book"),
    date_str: Optional[str] = Query(
        None, description="Date in YYYY-MM-DD (interpreted in salon local tz). If omitted, returns next available slots from today"),
    slot_padding_minutes: Optional[int] = Query(
        0, description="Extra padding in minutes between slots (default 0)"),
    max_slots: Optional[int] = Query(
        10, description="Maximum number of slots to return (default 10)"),
    days_ahead: Optional[int] = Query(
        7, description="If date omitted, search up to N days ahead (default 7)"),
    db: Session = Depends(get_db),
):
    """
    Returns available start/end slots for a salon and service.
    Uses the salon's timezone and `work_start_hour`/`work_end_hour` stored in DB.
    Returns local times (salon tz) and UTC times.
    
    Note: This endpoint does not require authentication as availability is public.
    """
    salon = db.query(models.Salon).filter(models.Salon.id == salon_id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")

    # Service validation removed: using fixed 1-hour slots
    # service = db.query(models.Service).filter(
    #     models.Service.id == service_id, models.Service.salon_id == salon_id).first()
    # if not service:
    #     raise HTTPException(
    #         status_code=404, detail="Service not found for the given salon")

    # validate timezone on salon
    # validate timezone on salon
    salon_tz_str = salon.timezone or "UTC"
    if salon_tz_str == "UTC":
        tz = timezone.utc
    else:
        try:
            tz = ZoneInfo(salon_tz_str)
        except Exception:
            # fallback to UTC if invalid
            tz = timezone.utc

    def _fetch_bookings_between(start_dt_utc: datetime, end_dt_utc: datetime):
        return db.query(models.Booking).filter(
            models.Booking.salon_id == salon_id,
            models.Booking.start_time < end_dt_utc,
            models.Booking.end_time > start_dt_utc,
            models.Booking.status.in_(
                [models.BookingStatus.pending.value, models.BookingStatus.approved.value])
        ).all()
    print("_fetch_bookings_between", _fetch_bookings_between)
    result_slots = []

    def _generate_for_day_local(local_day: date):
        # working hours are in salon's local timezone hours
        start_hour = salon.work_start_hour if salon.work_start_hour is not None else 9
        end_hour = salon.work_end_hour if salon.work_end_hour is not None else 18

        # local tz-aware window start/end
        local_window_start = datetime.combine(
            local_day, time(hour=start_hour, minute=0, second=0))
        local_window_start = local_window_start.replace(tzinfo=tz)
        local_window_end = datetime.combine(
            local_day, time(hour=end_hour, minute=0, second=0))
        local_window_end = local_window_end.replace(tzinfo=tz)

        # convert to UTC for DB comparisons (DB stores UTC)
        window_start_utc = local_window_start.astimezone(timezone.utc)
        window_end_utc = local_window_end.astimezone(timezone.utc)

        # fetch existing bookings overlapping this window
        existing = _fetch_bookings_between(window_start_utc, window_end_utc)
        blocked = [(b.start_time, b.end_time) for b in existing]

        # Fixed 1-hour slot length
        slot_length = timedelta(minutes=60)
        padding = timedelta(minutes=slot_padding_minutes or 0)

        # cursor should step in slot_length + padding
        cursor_local = local_window_start

        while cursor_local + slot_length <= local_window_end:
            candidate_start_local = cursor_local
            candidate_end_local = cursor_local + slot_length

            # convert candidate to UTC to compare with booking times in DB
            candidate_start_utc = candidate_start_local.astimezone(
                timezone.utc)
            candidate_end_utc = candidate_end_local.astimezone(timezone.utc)
            padded_end_utc = candidate_end_utc + padding

            conflict = False
            for (b_start, b_end) in blocked:
                if _overlaps(candidate_start_utc, padded_end_utc, b_start, b_end):
                    conflict = True
                    break

            if not conflict:
                result_slots.append({
                    "start_time_local": candidate_start_local.isoformat(),
                    "end_time_local": candidate_end_local.isoformat(),
                    "start_time_utc": candidate_start_utc.isoformat(),
                    "end_time_utc": candidate_end_utc.isoformat(),
                    "tz": salon.timezone or "UTC"
                })
                if len(result_slots) >= max_slots:
                    return

            # Move cursor to the end of the current slot plus padding
            cursor_local = cursor_local + slot_length + padding

    if date_str:
        try:
            # parse date in YYYY-MM-DD and interpret as date in salon local tz
            local_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=400, detail="date must be YYYY-MM-DD")
        _generate_for_day_local(local_date)
    else:
        today_local = datetime.now(tz).date()
        for d_offset in range(days_ahead or 7):
            _generate_for_day_local(today_local + timedelta(days=d_offset))
            if len(result_slots) >= max_slots:
                break

    return result_slots
