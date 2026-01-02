from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Driver, User, DriverLocation, Order
from app.schemas import DriverCreate, DriverOut, DriverUpdate, DriverSettingsUpdate
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=DriverOut)
def create_driver(driver: DriverCreate, db: Session = Depends(get_db)):
    db_driver = Driver(**driver.dict())
    db.add(db_driver)
    db.commit()
    db.refresh(db_driver)
    return db_driver

@router.patch("/status", response_model=DriverOut)
def update_driver_status(
    status_update: DriverUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can update status"
        )
    
    previous_status = driver.is_online
    driver.is_online = status_update.is_online
    
    # If transitioning from offline to online and lat/lng provided, record location (UPSERT)
    if not previous_status and status_update.is_online and status_update.lat is not None and status_update.lng is not None:
        db_location = db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).first()
        if db_location:
            db_location.lat = status_update.lat
            db_location.lng = status_update.lng
            db_location.recorded_at = datetime.utcnow()
        else:
            db_location = DriverLocation(
                driver_id=driver.id,
                lat=status_update.lat,
                lng=status_update.lng
            )
            db.add(db_location)
    
    db.commit()
    db.refresh(driver)
    return driver

@router.patch("/settings", response_model=DriverOut)
def update_driver_settings(
    settings_update: DriverSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can update settings"
        )
    
    # Validate and update work_radius_km
    if settings_update.work_radius_km is not None:
        if settings_update.work_radius_km < 2.0 or settings_update.work_radius_km > 50.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Work radius must be between 2 and 50 kilometers"
            )
        driver.work_radius_km = settings_update.work_radius_km
    
    db.commit()
    db.refresh(driver)
    return driver

@router.get("/earnings/summary")
def get_earnings_summary(
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view earnings"
        )
    
    # Calculate date range based on period
    now = datetime.utcnow()
    
    if period == "daily":
        start_date = now - timedelta(days=1)
        end_date = now
    elif period == "weekly":
        start_date = now - timedelta(days=7)
        end_date = now
    else:  # monthly
        start_date = now - timedelta(days=30)
        end_date = now
    
    # Query completed orders for this driver in the date range
    orders = db.query(Order).filter(
        Order.driver_id == driver.id,
        Order.status == 'completed',
        Order.created_at >= start_date,
        Order.created_at <= end_date
    ).all()
    
    # Calculate totals
    total_orders = len(orders)
    total_price = sum(float(order.price or 0) for order in orders)
    total_platform_fee = sum(float(order.platform_fee or 0) for order in orders)
    total_driver_earnings = sum(float(order.driver_earnings or 0) for order in orders)
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_orders": total_orders,
        "total_price": round(total_price, 2),
        "total_platform_fee": round(total_platform_fee, 2),
        "total_driver_earnings": round(total_driver_earnings, 2)
    }

@router.get("/stats")
def get_driver_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view stats"
        )
    
    # Calculate total completed trips
    total_trips = db.query(Order).filter(
        Order.driver_id == driver.id,
        Order.status == 'completed'
    ).count()
    
    # Calculate years active (from driver created_at to now)
    if driver.created_at:
        years_active = (datetime.utcnow() - driver.created_at).days / 365.25
        years_active = max(0, int(years_active))  # Ensure non-negative integer
    else:
        years_active = 0
    
    # TODO: Calculate rating from reviews table when implemented
    # For now, return 5.0 as default (perfect rating)
    rating = 5.0
    
    return {
        "rating": rating,
        "total_trips": total_trips,
        "years_active": years_active
    }

@router.get("/", response_model=list[DriverOut])
def list_drivers(db: Session = Depends(get_db)):
    return db.query(Driver).all()

@router.get("/{driver_id}", response_model=DriverOut)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    db_driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not db_driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return db_driver

