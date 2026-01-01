from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import OrderTracking
from app.schemas import OrderTrackingCreate, OrderTrackingOut

router = APIRouter()

@router.post("/", response_model=OrderTrackingOut)
def create_tracking(tracking: OrderTrackingCreate, db: Session = Depends(get_db)):
    db_tracking = OrderTracking(**tracking.dict())
    db.add(db_tracking)
    db.commit()
    db.refresh(db_tracking)
    return db_tracking

@router.get("/", response_model=list[OrderTrackingOut])
def list_tracking(db: Session = Depends(get_db)):
    return db.query(OrderTracking).all()

@router.get("/{tracking_id}", response_model=OrderTrackingOut)
def get_tracking(tracking_id: int, db: Session = Depends(get_db)):
    db_tracking = db.query(OrderTracking).filter(OrderTracking.id == tracking_id).first()
    if not db_tracking:
        raise HTTPException(status_code=404, detail="Tracking not found")
    return db_tracking
