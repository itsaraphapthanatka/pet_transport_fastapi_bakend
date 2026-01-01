from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationOut
from app.core.security import get_current_user

router = APIRouter()

@router.post("/", response_model=NotificationOut)
def create_notification(notification: NotificationCreate, db: Session = Depends(get_db)):
    db_notification = Notification(**notification.dict())
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@router.get("/", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Filter by current user and order by created_at descending (newest first)
    return db.query(Notification)\
        .filter(Notification.user_id == current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()

@router.get("/{notification_id}", response_model=NotificationOut)
def get_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return db_notification

@router.put("/{notification_id}/read", response_model=NotificationOut)
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    db_notification.is_read = True
    db.commit()
    db.refresh(db_notification)
    return db_notification
