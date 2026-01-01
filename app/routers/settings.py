from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import PlatformSettings
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class SettingUpdate(BaseModel):
    value: str

class SettingOut(BaseModel):
    key: str
    value: str
    description: Optional[str] = None
    
    class Config:
        orm_mode = True

def get_setting(db: Session, key: str, default: str = None) -> str:
    """Helper function to get a setting value from database"""
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()
    if setting:
        return setting.value
    return default

@router.get("/{key}", response_model=SettingOut)
def get_setting_by_key(key: str, db: Session = Depends(get_db)):
    """Get a specific setting by key"""
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    return setting

@router.get("/", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    """Get all platform settings"""
    return db.query(PlatformSettings).all()

@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    setting_update: SettingUpdate,
    db: Session = Depends(get_db)
    # TODO: Add admin authentication
    # current_user: User = Depends(get_current_admin_user)
):
    """Update a setting value (admin only)"""
    setting = db.query(PlatformSettings).filter(PlatformSettings.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    
    setting.value = setting_update.value
    db.commit()
    db.refresh(setting)
    return setting
