from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, TIMESTAMP, Float, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)

    # LOGIN
    password_hash = Column(Text, nullable=False)

    # PROFILE
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), unique=True)
    email = Column(String(255), unique=True)
    role = Column(String(20), default="customer")

    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    pets = relationship("Pet", back_populates="owner")
    orders = relationship("Order", back_populates="customer")

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    vehicle_type = Column(String(50))
    vehicle_plate = Column(String(50))
    is_online = Column(Boolean, default=False)
    work_radius_km = Column(Float, default=10.0)  # Driver's work acceptance radius in kilometers
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    user = relationship("User")
    orders = relationship("Order", back_populates="driver")

class Pet(Base):
    __tablename__ = "pets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    type = Column(String(100))
    breed = Column(String(100))
    weight = Column(Numeric(10,2))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    owner = relationship("User", back_populates="pets")
    # orders = relationship("Order", back_populates="pet")
    orders = relationship("Order", secondary="order_pets", back_populates="pets")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    pet_id = Column(Integer, ForeignKey("pets.id"))
    
    pickup_address = Column(Text, nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    dropoff_address = Column(Text, nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)

    customer_lat = Column(Float, nullable=True)
    customer_lng = Column(Float, nullable=True)

    status = Column(String(20), default="pending")
    price = Column(Numeric(10,2))
    platform_fee = Column(Numeric(10,2))  # 7% commission for platform
    driver_earnings = Column(Numeric(10,2))  # 93% earnings for driver
    commission_rate = Column(Numeric(5,4))  # Store commission rate used (e.g., 0.0700 for 7%)
    passengers = Column(Integer, default=1)
    pet_details = Column(Text) # Store summarized pet details (e.g. "Milo, Luna")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

    customer = relationship("User", back_populates="orders")
    driver = relationship("Driver", back_populates="orders")
    # pet = relationship("Pet", back_populates="orders") # Deprecated: verify if we can remove safe
    pets = relationship("Pet", secondary="order_pets", back_populates="orders")

class OrderPet(Base):
    __tablename__ = "order_pets"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    pet_id = Column(Integer, ForeignKey("pets.id", ondelete="CASCADE"))
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class DriverLocation(Base):
    __tablename__ = "driver_locations"
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"))
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    recorded_at = Column(TIMESTAMP, default=datetime.utcnow)

    driver = relationship("Driver")

class OrderTracking(Base):
    __tablename__ = "order_tracking"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    recorded_at = Column(TIMESTAMP, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class PlatformSettings(Base):
    __tablename__ = "platform_settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(String(255), nullable=False)
    description = Column(Text)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)


class OTPCode(Base):
    __tablename__ = "otp_codes"
    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), nullable=False)
    otp = Column(String(6), nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    

class Settings(Base):
    __tablename__ = "settings" 
    id = Column(Integer, primary_key=True, index=True)
    map = Column(String(255), nullable=False)
    
    def __repr__(self):
        return f"<Settings(id={self.id}, map='{self.map}')>"

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, index=True)
    sender_id = Column(Integer)
    sender_role = Column(String)  # customer | driver
    message = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_read = Column(Boolean, default=False)

class ChatTyping(Base):
    __tablename__ = "chat_typing"

    order_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, primary_key=True)
    role = Column(String)
    is_typing = Column(Boolean, default=False)
class DeclinedOrder(Base):
    __tablename__ = "declined_orders"
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id", ondelete="CASCADE"))
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    created_at = Column(TIMESTAMP, default=func.now())

    driver = relationship("Driver")
    order = relationship("Order")
class PetType(Base):
    __tablename__ = "pet_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    icon = Column(String(50)) # e.g. "🐶"
