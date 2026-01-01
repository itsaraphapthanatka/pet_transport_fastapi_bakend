from fastapi import WebSocket
from app.core.redis import publish
from app.database import SessionLocal
from app.models import ChatMessage
import json

active_connections = {}

async def chat_ws(
    websocket: WebSocket,
    order_id: int,
    user_id: int,
    role: str
):
    await websocket.accept()
    key = f"{order_id}:{user_id}"
    active_connections[key] = websocket

    try:
        while True:
            data = await websocket.receive_json()

            print(f"Received data: {data}")  # Debug log
            
            # typing indicator
            if data.get("type") == "typing":
                await publish(f"chat:{order_id}", {
                    "type": "typing",
                    "user_id": user_id,
                    "role": role,
                    "is_typing": data["is_typing"]
                })
                continue

            # send message
            db = SessionLocal()
            msg = ChatMessage(
                order_id=order_id,
                sender_id=user_id,
                sender_role=role,
                message=data.get("message"),
                media_url=data.get("media_url")
            )
            db.add(msg)
            db.commit()
            db.refresh(msg)

            payload = {
                "type": "message",
                "id": msg.id,
                "order_id": order_id,
                "sender_id": user_id,
                "role": role,
                "message": msg.message,
                "media_url": msg.media_url,
                "created_at": str(msg.created_at)
            }

            await publish(f"chat:{order_id}", payload)

    except Exception as e:
        print(f"WebSocket Error: {e}")
        if key in active_connections:
            del active_connections[key]
