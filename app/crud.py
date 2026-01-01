from sqlalchemy.orm import Session
from app import models, schemas
from app.core.security import get_password_hash, verify_password
from app.models import ChatMessage, OTPCode
from datetime import datetime

# ---------- USER ----------
def create_user(db: Session, user: schemas.UserCreate):
    hashed_pw = get_password_hash(user.password)

    db_user = models.User(
        full_name=user.full_name,
        phone=user.phone,
        email=user.email,
        password_hash=hashed_pw
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_phone(db: Session, phone: str):
    return db.query(models.User).filter(models.User.phone == phone).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def authenticate_user(db: Session, identifier: str, password: str):
    """
    Authenticate user by email or phone with password
    """
    # Try to find user by email or phone
    user = get_user_by_email(db, identifier)
    if not user:
        user = get_user_by_phone(db, identifier)
    
    if not user:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    return user


def create_or_get_user_by_phone(db: Session, phone: str, full_name: str = None):
    """
    Get existing user by phone or create new one
    Used for OTP-based registration
    """
    user = get_user_by_phone(db, phone)
    if user:
        return user
    
    # Create new user with phone only
    # Generate a random password hash for OTP users (they won't use password login)
    import secrets
    random_password = secrets.token_urlsafe(32)
    
    db_user = models.User(
        phone=phone,
        full_name=full_name or f"User {phone[-4:]}",
        password_hash=get_password_hash(random_password),
        role="customer"
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user: schemas.UserCreate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None

    db_user.full_name = user.full_name
    db_user.phone = user.phone
    db_user.email = user.email
    db_user.password_hash = get_password_hash(user.password)

    db.commit()
    db.refresh(db_user)
    return db_user


def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None

    db.delete(db_user)
    db.commit()
    return db_user


# ---------- DRIVER ----------
def create_driver(db: Session, driver: schemas.DriverCreate):
    db_driver = models.Driver(**driver.dict())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver


def get_drivers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Driver).offset(skip).limit(limit).all()


# ---------- PET ----------
def create_pet(db: Session, pet: schemas.PetCreate):
    db_pet = models.Pet(**pet.dict())
    db.add(db_pet)
    db.commit()
    db.refresh(db_pet)
    return db_pet


def get_pets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Pet).offset(skip).limit(limit).all()


# ---------- DRIVER LOCATION ----------
def create_driver_location(db: Session, location: schemas.DriverLocationCreate):
    db_location = models.DriverLocation(**location.dict())
    db.add(db_location)
    db.commit()
    db.refresh(db_location)
    return db_location


def get_driver_locations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DriverLocation).offset(skip).limit(limit).all()


def create_chat_message(
    db: Session,
    order_id: int,
    sender_id: int,
    sender_role: str,
    message: str
):
    chat = ChatMessage(
        order_id=order_id,
        sender_id=sender_id,
        sender_role=sender_role,
        message=message
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat

def get_chat_history(db: Session, order_id: int):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.order_id == order_id)
        .order_by(ChatMessage.created_at)
        .all()
    )


# ---------- OTP ----------
def save_otp(db: Session, phone: str, otp: str, expires_at: datetime):
    """
    Save OTP to database
    """
    # Delete any existing OTP for this phone
    db.query(OTPCode).filter(OTPCode.phone == phone).delete()
    
    db_otp = OTPCode(
        phone=phone,
        otp=otp,
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    return db_otp


def verify_and_consume_otp(db: Session, phone: str, otp: str):
    """
    Verify OTP and delete it if valid
    Returns True if valid, False otherwise
    """
    otp_record = db.query(OTPCode).filter(
        OTPCode.phone == phone,
        OTPCode.otp == otp
    ).first()
    
    if not otp_record:
        return False
    
    # Check if expired
    if otp_record.expires_at < datetime.utcnow():
        db.delete(otp_record)
        db.commit()
        return False
    
    # Valid OTP, delete it
    db.delete(otp_record)
    db.commit()
    return True


def cleanup_expired_otps(db: Session):
    """
    Delete all expired OTPs
    """
    db.query(OTPCode).filter(OTPCode.expires_at < datetime.utcnow()).delete()
    db.commit()