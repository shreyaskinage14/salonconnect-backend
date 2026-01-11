# app/api/v1/services.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from crud.service import create_service, get_service, list_services_by_salon, update_service, delete_service
from crud.salon import get_salon
from schemas import ServiceCreate, ServiceOut, ServiceUpdate
from api.deps import get_db, get_current_user
from app.db.models import User

router = APIRouter()

def _check_service_authorization(db: Session, user: User, salon_id: int):
    """
    Check if the user is authorized to manage services for the given salon.
    Authorized if admin (role "0") or salon owner (role "2") of the specific salon.
    """
    if str(user.role) == "0":
        return True
    
    salon = get_salon(db, salon_id)
    if not salon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")
    
    if salon.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="You do not have permission to manage services for this salon"
        )
    return True

@router.post("/", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_new_service(
    service_in: ServiceCreate,
    salon_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new service for a salon.
    Requires authentication and salon ownership or admin role.
    """
    _check_service_authorization(db, current_user, salon_id)
    return create_service(db, salon_id=salon_id, service_in=service_in)

@router.get("/{service_id}", response_model=ServiceOut)
def read_service(service_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific service.
    """
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service

@router.get("/salon/{salon_id}", response_model=List[ServiceOut])
def list_salon_services(salon_id: int, db: Session = Depends(get_db)):
    """
    List all services offered by a specific salon.
    """
    # Check if salon exists
    salon = get_salon(db, salon_id)
    if not salon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salon not found")
    return list_services_by_salon(db, salon_id)

@router.patch("/{service_id}", response_model=ServiceOut)
def update_existing_service(
    service_id: int,
    service_in: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update details of a service.
    Requires authentication and salon ownership or admin role.
    """
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    _check_service_authorization(db, current_user, service.salon_id)
    return update_service(db, service_id, service_in)

@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_existing_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a service.
    Requires authentication and salon ownership or admin role.
    """
    service = get_service(db, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    
    _check_service_authorization(db, current_user, service.salon_id)
    if not delete_service(db, service_id):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete service")
    return None
