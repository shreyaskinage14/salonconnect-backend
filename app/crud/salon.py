# app/crud/salon.py
from sqlalchemy.orm import Session
from app.db import models
from typing import List
import math


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth (in kilometers).
    Uses the Haversine formula.
    """
    # Earth's radius in kilometers
    R = 6371.0
    
    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c


def create_salon(db: Session, owner_id: int, salon_in) -> models.Salon:
    salon = models.Salon(
        owner_id=owner_id,
        business_name=salon_in.business_name,
        description=salon_in.description,
        address=salon_in.address,
        lat=salon_in.lat,
        lng=salon_in.lng,
        phone=salon_in.phone,
        city=salon_in.city
    )
    db.add(salon)
    db.flush()  # get salon.id

    # add services if provided
    for s in salon_in.services or []:
        service = models.Service(
            salon_id=salon.id,
            name=s.name,
            description=s.description,
            duration_minutes=s.duration_minutes,
            price=s.price
        )
        db.add(service)

    db.commit()
    db.refresh(salon)
    return salon


def get_salon(db: Session, salon_id: int) -> models.Salon:
    return db.query(models.Salon).filter(models.Salon.id == salon_id).first()


def list_salons(db: Session, q: str = None, limit: int = 20, offset: int = 0) -> List[models.Salon]:
    query = db.query(models.Salon)
    if q:
        q_like = f"%{q}%"
        query = query.filter(models.Salon.business_name.ilike(q_like))
    return query.order_by(models.Salon.id.desc()).offset(offset).limit(limit).all()


def list_nearby_salons(
    db: Session,
    city: str,
    user_lat: float,
    user_lng: float,
    radius_km: float = 2.0,
    limit: int = 20
) -> List[dict]:
    """
    Find salons within a specified radius (default 2km) from the user's location,
    filtered by city.
    
    Args:
        db: Database session
        city: City name to filter salons (case-insensitive)
        user_lat: User's latitude
        user_lng: User's longitude
        radius_km: Search radius in kilometers (default: 2km)
        limit: Maximum number of results
    
    Returns a list of dicts with salon data and distance.
    """
    # First filter by city (case-insensitive), then get salons that have lat/lng set
    salons = db.query(models.Salon).filter(
        models.Salon.city.ilike(city),
        models.Salon.lat.isnot(None),
        models.Salon.lng.isnot(None)
    ).all()
    
    nearby = []
    for salon in salons:
        distance = haversine_distance(user_lat, user_lng, salon.lat, salon.lng)
        if distance <= radius_km:
            nearby.append({
                "salon": salon,
                "distance_km": round(distance, 2)
            })
    
    # Sort by distance (closest first)
    nearby.sort(key=lambda x: x["distance_km"])
    
    return nearby[:limit]
