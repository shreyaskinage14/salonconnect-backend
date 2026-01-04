from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from api.deps import get_db, get_current_user
from db.models import Employee, Service, Salon, User
from schemas import EmployeeCreate, EmployeeResponse

router = APIRouter()

@router.post("/create", response_model=EmployeeResponse)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check role "2" (owner) or "0" (admin)
    if str(current_user.role) not in ["0", "2"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only salon owners or admins can add employees"
        )

    # Resolve Salon ID
    salon_id = None
    
    # CASE 1: Salon ID provided explicitly
    if employee.salon_id:
        # If user is admin, allow any salon
        if str(current_user.role) == "0":
            salon_id = employee.salon_id
        # If user is owner, ensure they own it
        else:
            salon = db.query(Salon).filter(Salon.id == employee.salon_id, Salon.owner_id == current_user.id).first()
            if not salon:
                raise HTTPException(status_code=403, detail="You do not own this salon")
            salon_id = salon.id
            
    # CASE 2: Infer Salon ID from owner
    else:
        # If admin, required field
        if str(current_user.role) == "0":
            raise HTTPException(status_code=400, detail="Admin must specify salon_id")
            
        # If owner, find their salon
        salon = db.query(Salon).filter(Salon.owner_id == current_user.id).first()
        if not salon:
            raise HTTPException(status_code=404, detail="Salon not found")
        salon_id = salon.id

    # Check service belongs to this salon
    service = db.query(Service).filter(
        Service.id == employee.service_id,
        Service.salon_id == salon_id
    ).first()

    if not service:
        raise HTTPException(status_code=400, detail="Service does not belong to the specified salon")

    new_employee = Employee(
        name=employee.name,
        experience_years=employee.experience_years,
        service_id=employee.service_id,
        salon_id=salon_id
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
    if current_user.role != "2" or current_user.role != "0":
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
