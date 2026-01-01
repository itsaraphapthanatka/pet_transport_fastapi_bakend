# app/routers/driver_ws.py
from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/driver/{driver_id}")
async def driver_ws(websocket: WebSocket, driver_id: int):
    await websocket.accept()
    while True:
        try:
            data = await websocket.receive_json()
            print(f"Driver {driver_id} location:", data)
            await websocket.send_json(data)  # echo กลับ client
        except Exception:
            break
