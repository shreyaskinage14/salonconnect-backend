# app/crud/service.py
from sqlalchemy.orm import Session
from app.db import models
from typing import List, Optional

def create_service(db: Session, salon_id: int, service_in) -> models.Service:
    """
    Create a new service for a specific salon.
    """
    service = models.Service(
        salon_id=salon_id,
        name=service_in.name,
        description=service_in.description,
        duration_minutes=service_in.duration_minutes,
        price=service_in.price
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

def get_service(db: Session, service_id: int) -> Optional[models.Service]:
    """
    Retrieve a single service by its ID.
    """
    return db.query(models.Service).filter(models.Service.id == service_id).first()

def list_services_by_salon(db: Session, salon_id: int) -> List[models.Service]:
    """
    Retrieve all services offered by a specific salon.
    """
    return db.query(models.Service).filter(models.Service.salon_id == salon_id).all()

def update_service(db: Session, service_id: int, service_in) -> Optional[models.Service]:
    """
    Update service details.
    """
    service = get_service(db, service_id)
    if not service:
        return None
    
    # Update only fields that are provided
    update_data = service_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)
    
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

def delete_service(db: Session, service_id: int) -> bool:
    """
    Delete a service.
    """
    service = get_service(db, service_id)
    if not service:
        return False
    
    db.delete(service)
    db.commit()
    return True
