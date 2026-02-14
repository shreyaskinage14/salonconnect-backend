# app/api/v1/salons.py
"""
Salon management API endpoints.
All endpoints require Bearer token authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field

from crud.salon import create_salon, get_salon, list_salons, list_nearby_salons
from crud.user import create_user, get_user_by_email
from schemas import SalonCreate, SalonOut
from api.deps import get_db, get_current_user
from core.security import decode_access_token
from app.db.models import User
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from api.deps import bearer_scheme, optional_bearer_scheme

router = APIRouter()


# =============================================================================
# Request/Response Schemas
# =============================================================================

class NearbySearchRequest(BaseModel):
    """Request schema for nearby salon search."""
    city: str = Field(..., min_length=1, description="City name to filter salons (required)")
    lat: float = Field(..., ge=-90, le=90, description="User's latitude (-90 to 90)")
    lng: float = Field(..., ge=-180, le=180, description="User's longitude (-180 to 180)")
    radius_km: Optional[float] = Field(2.0, ge=0.1, le=50.0, description="Search radius in kilometers (default: 2km, max: 50km)")
    limit: Optional[int] = Field(20, ge=1, le=100, description="Maximum number of results (default: 20, max: 100)")

    class Config:
        json_schema_extra = {
            "example": {
                "city": "Mumbai",
                "lat": 19.0760,
                "lng": 72.8777,
                "radius_km": 5.0,
                "limit": 20
            }
        }


class NearbySalonOut(BaseModel):
    """Response schema for nearby salon with distance."""
    salon: SalonOut
    distance_km: float = Field(..., ge=0, description="Distance from user in kilometers")


class SalonHoursUpdate(BaseModel):
    """Request schema for updating salon hours."""
    timezone: Optional[str] = Field(None, description="IANA timezone string, e.g. 'Asia/Kolkata'")
    work_start_hour: Optional[int] = Field(None, ge=0, le=23, description="Start hour in 24h format (0-23)")
    work_end_hour: Optional[int] = Field(None, ge=0, le=23, description="End hour in 24h format (0-23)")

    class Config:
        json_schema_extra = {
            "example": {
                "timezone": "Asia/Kolkata",
                "work_start_hour": 9,
                "work_end_hour": 21
            }
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _serialize_service(svc) -> dict:
    """Convert Service model to dictionary."""
    if svc is None:
        return None
    return {
        "id": svc.id,
        "name": svc.name,
        "description": svc.description,
        "duration_minutes": svc.duration_minutes,
        "price": float(svc.price) if svc.price is not None else None,
    }


def _serialize_salon(salon) -> dict:
    """Convert Salon model to SalonOut-compatible dictionary."""
    if salon is None:
        return None
    return {
        "id": salon.id,
        "owner_id": salon.owner_id,
        "business_name": salon.business_name,
        "description": salon.description,
        "address": salon.address,
        "lat": salon.lat,
        "lng": salon.lng,
        "phone": salon.phone,
        "timezone": salon.timezone,
        "work_start_hour": salon.work_start_hour,
        "work_end_hour": salon.work_end_hour,
        "created_at": salon.created_at.isoformat() if salon.created_at else None,
        "city": salon.city,
        "services": [_serialize_service(svc) for svc in (salon.services or [])],
    }


def _check_salon_ownership(salon, user: User) -> None:
    """
    Verify that the user is the salon owner or an admin.
    Raises HTTPException 403 if not authorized.
    """
    # Role "0" = admin, owner_id match = owner
    is_admin = str(user.role) == "0"
    is_owner = salon.owner_id == user.id
    
    if not (is_admin or is_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this salon"
        )


# =============================================================================
# Salon CRUD Endpoints
# =============================================================================

@router.post("/create", response_model=SalonOut, status_code=status.HTTP_201_CREATED)
def create_salon_endpoint(
    salon_in: SalonCreate,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_bearer_scheme)
):
    """
    Create a new salon.
    
    **If owner_details provided**: Creates a new owner user and links it to the salon. No token required.
    **If owner_details NOT provided**: Requires Bearer token authentication to use the current user as owner.
    """
    owner_id = None
    
    # CASE 1: Create a new owner if details are provided
    if salon_in.owner_details:
        # Check if user already exists
        existing_user = get_user_by_email(db, salon_in.owner_details.email)
        if existing_user:
            # Use existing user as owner
            owner_id = existing_user.id
        else:
            # Create new owner (role "2")
            new_owner = create_user(
                db,
                email=salon_in.owner_details.email,
                password=salon_in.owner_details.password,
                name=salon_in.owner_details.name,
                phone=salon_in.owner_details.phone,
                role=2  # Owner role
            )
            owner_id = new_owner.id
    
    # CASE 2: Use current authenticated user if no new owner details provided
    else:
        if not credentials:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Provide owner_details or a Bearer token."
            )
        
        # Manually validate token directly to avoid dependency issues
        token = credentials.credentials
        email = decode_access_token(token)
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        owner_id = user.id

    salon = create_salon(db, owner_id=owner_id, salon_in=salon_in)
    return _serialize_salon(salon)


@router.get("/list", response_model=List[SalonOut])
def list_salons_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None, description="Search query for business name"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    List all salons with optional search filter.
    
    **Requires**: Bearer token authentication  
    **Query Parameters**:
    - `q`: Search query for business name (optional)
    - `limit`: Max results (default: 20, max: 100)
    - `offset`: Pagination offset (default: 0)
    """
    salons = list_salons(db, q=q, limit=limit, offset=offset)
    return [_serialize_salon(s) for s in salons]


@router.post("/nearby", response_model=List[NearbySalonOut])
def get_nearby_salons(
    payload: NearbySearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find salons near a location, filtered by city.
    
    **Requires**: Bearer token authentication  
    **Request Body**:
    - `city`: City name to filter salons (required, case-insensitive)
    - `lat`: User's latitude
    - `lng`: User's longitude
    - `radius_km`: Search radius in kilometers (default: 2km, max: 50km)
    - `limit`: Maximum results (default: 20)
    
    **Returns**: Salons sorted by distance (closest first) with distance in km.
    """
    nearby = list_nearby_salons(
        db,
        city=payload.city,
        user_lat=payload.lat,
        user_lng=payload.lng,
        radius_km=payload.radius_km or 2.0,
        limit=payload.limit or 20
    )
    
    return [
        NearbySalonOut(
            salon=_serialize_salon(item["salon"]),
            distance_km=item["distance_km"]
        )
        for item in nearby
    ]


@router.get("/{salon_id}", response_model=SalonOut)
def get_salon_endpoint(
    salon_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific salon by ID.
    
    **Requires**: Bearer token authentication
    """
    salon = get_salon(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )
    return _serialize_salon(salon)


# =============================================================================
# Salon Update Endpoints
# =============================================================================

@router.patch("/{salon_id}/hours", response_model=SalonOut)
def update_salon_hours(
    salon_id: int,
    payload: SalonHoursUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update salon timezone and working hours.
    
    **Requires**: Bearer token authentication  
    **Authorization**: Salon owner or admin only
    
    **Request Body** (all optional):
    - `timezone`: IANA timezone string (e.g., 'Asia/Kolkata')
    - `work_start_hour`: Start hour in 24h format (0-23)
    - `work_end_hour`: End hour in 24h format (0-23)
    """
    salon = get_salon(db, salon_id)
    if not salon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found"
        )

    # Check authorization
    _check_salon_ownership(salon, current_user)

    # Apply updates (only fields provided)
    updated = False
    if payload.timezone is not None:
        salon.timezone = payload.timezone
        updated = True
    if payload.work_start_hour is not None:
        salon.work_start_hour = payload.work_start_hour
        updated = True
    if payload.work_end_hour is not None:
        salon.work_end_hour = payload.work_end_hour
        updated = True

    if updated:
        db.add(salon)
        db.commit()
        db.refresh(salon)

    return _serialize_salon(salon)
