from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


# ---------- User ----------
class UserBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    wallet_balance: Optional[Decimal] = Decimal("0.0")
    stripe_customer_id: Optional[str] = None


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str
    password: str

class UserOut(UserBase):
    id: int
    class Config:
        from_attributes = True

# ---------- Driver ----------
class DriverBase(BaseModel):
    user_id: int
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None
    is_online: bool = False
    work_radius_km: float = 10.0


class DriverCreate(DriverBase):
    pass

class DriverUpdate(BaseModel):
    is_online: bool
    lat: Optional[float] = None
    lng: Optional[float] = None

class DriverSettingsUpdate(BaseModel):
    work_radius_km: Optional[float] = None

class DriverOut(DriverBase):
    id: int
    user: UserOut
    class Config:
        from_attributes = True

# ---------- Pet ----------
class PetBase(BaseModel):
    user_id: Optional[int] = None
    name: str
    type: Optional[str] = None
    breed: Optional[str] = None
    weight: Optional[float] = None

class PetCreate(PetBase):
    pass

class PetOut(PetBase):
    id: int
    owner: UserOut
    class Config:
        from_attributes = True

# ---------- Pet Type ----------
class PetTypeBase(BaseModel):
    name: str
    icon: Optional[str] = None

class PetTypeOut(PetTypeBase):
    id: int
    class Config:
        from_attributes = True

# ---------- Order ----------
class OrderBase(BaseModel):
    user_id: Optional[int] = None
    driver_id: Optional[int] = None
    pet_id: int
    pickup_address: str
    pickup_lat: float
    pickup_lng: float
    dropoff_address: str
    dropoff_lat: float
    dropoff_lng: float
    status: Optional[str] = "pending"
    price: Optional[Decimal] = None
    platform_fee: Optional[Decimal] = None
    driver_earnings: Optional[Decimal] = None
    commission_rate: Optional[Decimal] = None

    passengers: Optional[int] = 1
    pet_details: Optional[str] = None
    customer_lat: Optional[float] = None
    customer_lng: Optional[float] = None
    payment_status: Optional[str] = "pending"
    payment_method: Optional[str] = "cash"
    created_at: Optional[datetime] = None

class OrderCreate(OrderBase):
    pet_ids: Optional[List[int]] = None

class OrderUpdate(BaseModel):
    status: Optional[str] = None
    driver_id: Optional[int] = None
    price: Optional[Decimal] = None

    customer_lat: Optional[float] = None
    customer_lng: Optional[float] = None
    payment_status: Optional[str] = None
    payment_method: Optional[str] = None

class OrderOut(OrderBase):
    id: int
    customer: UserOut
    driver: Optional[DriverOut] = None
    pet: Optional[PetOut] = None # Keeping for backward compatibility
    pets: List[PetOut] = []
    class Config:
        from_attributes = True

# ---------- Driver Location ----------
class DriverLocationBase(BaseModel):
    driver_id: int
    lat: float
    lng: float

class DriverLocationCreate(DriverLocationBase):
    pass

class DriverLocationInput(BaseModel):
    lat: float
    lng: float

class DriverLocationOut(DriverLocationBase):
    id: int
    driver: Optional[DriverOut] = None
    class Config:
        from_attributes = True

# ---------- OrderTracking ----------
class OrderTrackingBase(BaseModel):
    order_id: int
    driver_id: int
    lat: float
    lng: float

class OrderTrackingCreate(OrderTrackingBase):
    pass

class OrderTrackingOut(OrderTrackingBase):
    id: int
    class Config:
        from_attributes = True

# ---------- Notification ----------
class NotificationBase(BaseModel):
    user_id: int
    title: str
    message: str
    is_read: Optional[bool] = False

class NotificationCreate(NotificationBase):
    pass

class NotificationOut(NotificationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

# ---------- Authentication ----------
class LoginRequest(BaseModel):
    username: str  # email or phone
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str
    wallet_balance: Decimal = Decimal("0.0")
    stripe_customer_id: Optional[str] = None

    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ---------- Settings ----------
class SettingsBase(BaseModel):
    map: str

class SettingsCreate(SettingsBase):
    pass

class SettingsOut(SettingsBase):
    id: int
    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    order_id: int
    message: str

class ChatMessageOut(BaseModel):
    id: int
    order_id: int
    sender_id: int
    sender_role: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True
# ---------- Declined Order ----------
class DeclinedOrderCreate(BaseModel):
    order_id: int

class DeclinedOrderOut(BaseModel):
    id: int
    driver_id: int
    order_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ---------- Payment ----------
class PaymentBase(BaseModel):
    order_id: int
    amount: Decimal

    status: Optional[str] = "pending"
    method: Optional[str] = None
    transaction_id: Optional[str] = None

class PaymentCreate(PaymentBase):
    pass

class PaymentOut(PaymentBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True

class PaymentMethodOut(BaseModel):
    id: str
    brand: Optional[str] = None
    last4: Optional[str] = None
    exp_month: Optional[int] = None
    exp_year: Optional[int] = None

class SetupIntentResponse(BaseModel):
    setupIntent: str
    ephemeralKey: str
    customer: str
    publishableKey: Optional[str] = None

# ---------- Wallet ----------
class WalletTransactionBase(BaseModel):
    amount: Decimal

    type: str
    status: Optional[str] = "pending"
    reference_id: Optional[str] = None
    description: Optional[str] = None

class WalletTransactionCreate(WalletTransactionBase):
    pass

class WalletTransactionOut(WalletTransactionBase):
    id: int
    user_id: int
    created_at: datetime
    class Config:
        from_attributes = True

class WalletTopupRequest(BaseModel):
    amount: Decimal

    method: str = "promptpay"

class TopupIntentResponse(BaseModel):
    paymentIntent: str
    ephemeralKey: str
    customer: str
    publishableKey: Optional[str] = None
    transaction_id: int


