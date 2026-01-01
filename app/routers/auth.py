import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import create_access_token, get_current_user
from app import crud, schemas
from datetime import datetime, timedelta
import random
from pydantic import BaseModel, Field

router = APIRouter()

# Regex patterns
EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"
PHONE_REGEX = r"^\+66\d{8,9}$"


# Request models
class OTPRequest(BaseModel):
    phone_number: str = Field(
        ..., 
        pattern=PHONE_REGEX, 
        description="Thai mobile phone number, e.g. +66812345678"
    )


class VerifyOTPRequest(BaseModel):
    phone_number: str
    otp: str


def create_otp():
    """Generate 6-digit OTP"""
    return f"{random.randint(100000, 999999)}"


@router.post("/register", response_model=schemas.TokenResponse)
def register(user_data: schemas.RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email/phone and password
    """
    # Validate that at least email or phone is provided
    if not user_data.email and not user_data.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either email or phone must be provided"
        )
    
    # Check if user already exists
    if user_data.email:
        existing_user = crud.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    if user_data.phone:
        existing_user = crud.get_user_by_phone(db, user_data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Create user
    user = crud.create_user(db, schemas.UserCreate(
        full_name=user_data.full_name,
        email=user_data.email,
        phone=user_data.phone,
        password=user_data.password
    ))
    
    # Generate token
    token = create_access_token({"sub": str(user.id)})
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserResponse.from_orm(user)
    )


@router.post("/login", response_model=schemas.TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login with email/phone and password
    Username field accepts either email or phone number
    """
    identifier = form_data.username
    password = form_data.password
    
    # Authenticate user
    user = crud.authenticate_user(db, identifier, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/phone or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    token = create_access_token({"sub": str(user.id)})
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserResponse.from_orm(user)
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_current_user_info(current_user = Depends(get_current_user)):
    """
    Get current user information from JWT token
    """
    return schemas.UserResponse.from_orm(current_user)


@router.post("/request-otp")
def request_otp(data: OTPRequest, db: Session = Depends(get_db)):
    """
    Request OTP for phone number
    Creates or retrieves user account
    """
    phone = data.phone_number
    
    # Validate phone format
    if not re.match(PHONE_REGEX, phone):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Thai phone number format"
        )
    
    # Generate OTP
    otp_code = create_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Save OTP to database
    crud.save_otp(db, phone, otp_code, expires_at)
    
    # TODO: Send SMS (currently just logging)
    print(f"📱 OTP for {phone}: {otp_code}")
    
    return {
        "status": "otp_sent",
        "message": f"OTP sent to {phone}",
        "expires_at": expires_at,
        "debug_otp": otp_code  # Remove this in production!
    }


@router.post("/verify-otp", response_model=schemas.TokenResponse)
def verify_otp(data: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Verify OTP and login/register user
    Creates new user if doesn't exist
    """
    # Verify OTP
    is_valid = crud.verify_and_consume_otp(db, data.phone_number, data.otp)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP"
        )
    
    # Get or create user
    user = crud.create_or_get_user_by_phone(db, data.phone_number)
    
    # Generate token
    token = create_access_token({"sub": str(user.id)})
    
    return schemas.TokenResponse(
        access_token=token,
        token_type="bearer",
        user=schemas.UserResponse.from_orm(user)
    )


@router.post("/cleanup-otps")
def cleanup_expired_otps(db: Session = Depends(get_db)):
    """
    Admin endpoint to cleanup expired OTPs
    """
    crud.cleanup_expired_otps(db)
    return {"status": "success", "message": "Expired OTPs cleaned up"}