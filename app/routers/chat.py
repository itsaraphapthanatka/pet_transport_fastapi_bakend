from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatMessage

router = APIRouter(prefix="/chat", tags=["Chat"])

@router.get("/{order_id}")
def get_chat(order_id: int, db: Session = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.order_id == order_id)
        .order_by(ChatMessage.created_at)
        .all()
    )

@router.post("/{order_id}/read")
def mark_read(order_id: int, user_id: int, db: Session = Depends(get_db)):
    db.query(ChatMessage)\
      .filter(ChatMessage.order_id == order_id)\
      .filter(ChatMessage.sender_id != user_id)\
      .update({"is_read": True})
    db.commit()
    return {"status": "ok"}

@router.post("/{order_id}/media")
async def upload_media(order_id: int, file: UploadFile = File(...)):
    path = f"uploads/chat/{order_id}_{file.filename}"
    with open(path, "wb") as f:
        f.write(await file.read())
    return {"url": f"/{path}"}
