# app/api/deps.py
"""
Shared dependencies for API routes.
All post-login APIs should use `get_current_user` to require bearer token authentication.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.crud.user import get_user_by_email
from app.core.security import decode_access_token

# HTTPBearer scheme - provides simple Bearer token input in Swagger UI
# Users first login via /api/auth/login, then paste the access_token here
bearer_scheme = HTTPBearer(
    scheme_name="Bearer Token",
    description="Enter the access_token from login response (without 'Bearer ' prefix)"
)

optional_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="Bearer Token (Optional)",
    description="Optional authentication for unified salon/user creation."
)


def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    Authentication dependency for protected endpoints.
    Validates the bearer token and returns the authenticated user.
    
    Usage:
        @router.get("/protected")
        def protected_route(current_user = Depends(get_current_user)):
            ...
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Extract token from HTTPAuthorizationCredentials
    token = credentials.credentials
    
    email = decode_access_token(token)
    if not email:
        raise credentials_exception
    
    user = get_user_by_email(db, email)
    if not user:
        raise credentials_exception
    
    return user


def get_current_active_user(current_user = Depends(get_current_user)):
    """
    Dependency that also checks if the user is active.
    Can be extended to check for is_active flag if needed.
    """
    # If you have an is_active field on user model, you can check it here:
    # if not current_user.is_active:
    #     raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user = Depends(get_current_user)):
    """
    Dependency for admin-only endpoints.
    """
    if current_user.role != "0":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_current_owner_user(current_user = Depends(get_current_user)):
    """
    Dependency for salon owner-only endpoints.
    """
    if current_user.role not in ("2", "0"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Salon owner access required"
        )
    return current_user
