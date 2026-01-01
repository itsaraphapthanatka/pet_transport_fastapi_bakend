from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

@router.get("/docs_ws")
async def ws_docs():
    return {
        "description": "Connect to WebSocket at /ws/driver/{driver_id}",
        "example_js": "const ws = new WebSocket('ws://127.0.0.1:8000/ws/driver/1');"
    }


@router.websocket("/driver/{driver_id}")
async def websocket_endpoint(websocket: WebSocket, driver_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # data example: {"lat": 13.756, "lng": 100.501, "order_id": 1}
            await manager.broadcast({
                "driver_id": driver_id,
                "lat": data.get("lat"),
                "lng": data.get("lng"),
                "order_id": data.get("order_id")
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
