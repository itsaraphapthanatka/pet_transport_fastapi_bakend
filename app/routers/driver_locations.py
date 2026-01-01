from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import DriverLocation, Driver, User
from app.schemas import DriverLocationCreate, DriverLocationOut, DriverLocationInput
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=DriverLocationOut)
def create_driver_location(
    location: DriverLocationInput, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=403, detail="Only drivers can update location")

    # UPSERT Logic: Check if location record already exists for this driver
    db_location = db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).first()
    
    if db_location:
        # Update existing
        db_location.lat = location.lat
        db_location.lng = location.lng
        db_location.recorded_at = datetime.utcnow()
    else:
        # Create new
        db_location = DriverLocation(
            driver_id=driver.id,
            lat=location.lat,
            lng=location.lng
        )
        db.add(db_location)
        
    db.commit()
    db.refresh(db_location)
    return db_location

@router.put("/me", response_model=DriverLocationOut)
def update_my_location(
    location: DriverLocationInput, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This now uses the upsert logic in create_driver_location
    return create_driver_location(location, db, current_user)

@router.put("/{driver_id}", response_model=DriverLocationOut)
def update_driver_location_by_id(
    driver_id: int,
    location: DriverLocationInput,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Validate user is driver and matches id
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
         raise HTTPException(status_code=403, detail="Only drivers can update location")
    
    if driver.id != driver_id:
        raise HTTPException(status_code=403, detail="Cannot update another driver's location")

    # Reuse upsert logic via create_driver_location for consistency
    return create_driver_location(location, db, current_user)

@router.get("/", response_model=list[DriverLocationOut])
def list_driver_locations(db: Session = Depends(get_db)):
    from sqlalchemy import func
    from sqlalchemy.orm import joinedload
    
    # Subquery to find the latest location ID for each driver
    latest_ids = db.query(func.max(DriverLocation.id)).group_by(DriverLocation.driver_id).subquery()
    
    # Final query: latest locations for drivers that are ONLINE
    locations = (
        db.query(DriverLocation)
        .options(joinedload(DriverLocation.driver))
        .join(Driver, DriverLocation.driver_id == Driver.id)
        .filter(Driver.is_online == True)
        .filter(DriverLocation.id.in_(latest_ids))
        .all()
    )
    return locations

@router.get("/driver/{driver_id}", response_model=DriverLocationOut)
def get_latest_driver_location(driver_id: int, db: Session = Depends(get_db)):
    # Get latest location for specific driver
    db_location = db.query(DriverLocation).filter(DriverLocation.driver_id == driver_id).order_by(DriverLocation.id.desc()).first()
    if not db_location:
        raise HTTPException(status_code=404, detail="Location not found for this driver")
    return db_location

@router.get("/{location_id}", response_model=DriverLocationOut)
def get_driver_location(location_id: int, db: Session = Depends(get_db)):
    db_location = db.query(DriverLocation).join(Driver).filter(DriverLocation.id == location_id).first()
    if not db_location:
         raise HTTPException(status_code=404, detail="Location not found")
    return db_location

@router.delete("/me")
def delete_my_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
         raise HTTPException(status_code=403, detail="Only drivers can delete locations")
    
    db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).delete()
    db.commit()
    return {"message": "All your location records have been deleted"}

@router.delete("/{location_id}")
def delete_driver_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_location = db.query(DriverLocation).filter(DriverLocation.id == location_id).first()
    if not db_location:
         raise HTTPException(status_code=404, detail="Location not found")
    
    # Check if admin or owner
    # First, get driver for current_user
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    
    # If user is not admin and not the owner driver
    is_admin = current_user.role == "admin"
    is_owner = driver and db_location.driver_id == driver.id
    
    if not is_admin and not is_owner:
        raise HTTPException(status_code=403, detail="Not authorized to delete this record")

    db.delete(db_location)
    db.commit()
    return {"message": "Location record deleted"}
