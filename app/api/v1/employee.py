from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api.deps import get_db, get_current_user
from app.db.models import Employee, Service, Salon, User
from schemas import EmployeeCreate, EmployeeResponse

router = APIRouter()

@router.post("/create", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(current_user)
    # Check role "2" is salon owner
    if current_user.role != "2":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only salon owners can add employees"
        )

    # Get salon of logged-in owner
    salon = db.query(Salon).filter(Salon.owner_id == current_user.id).first()
    if not salon:
        raise HTTPException(status_code=404, detail="Salon not found")
    print(salon.id)
    print(employee)
    # Check service belongs to this salon
    service = db.query(Service).filter(
        Service.id == employee.service_id,
        Service.salon_id == salon.id
    ).first()

    print(service)

    if not service:
        raise HTTPException(status_code=400, detail="Service does not belong to your salon")

    new_employee = Employee(
        name=employee.name,
        experience_years=employee.experience_years,
        service_id=employee.service_id,
        salon_id=salon.id
    )

    db.add(new_employee)
    db.commit()
    db.refresh(new_employee)

    return new_employee

@router.get("/list", response_model=List[EmployeeResponse])
def get_my_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "2":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    salon = db.query(Salon).filter(Salon.owner_id == current_user.id).first()
    if not salon:
         return []

    return db.query(Employee).filter(
        Employee.salon_id == salon.id,
        Employee.is_active == True
    ).all()

@router.get("/service/{service_id}", response_model=List[EmployeeResponse])
def get_employees_by_service(
    service_id: int, 
    db: Session = Depends(get_db)
):
    return db.query(Employee).filter(
        Employee.service_id == service_id,
        Employee.is_active == True
    ).all()
