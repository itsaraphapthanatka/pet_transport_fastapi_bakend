from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect
import asyncio
from app.database import Base, engine
from app.routers import users, drivers, pets, orders, driver_locations, order_tracking, notifications, live_tracking, driver_ws, auth, pricing, settings, payments, wallet
from fastapi.middleware.cors import CORSMiddleware
from app.routers.chat import router as chat_router
from app.routers.chat_ws import chat_ws
from app.core.chat_subscriber import listen_chat

app = FastAPI(title="Pet Transport API")

# ถ้าใช้ HTML/JS client จาก browser ต้องเปิด CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(drivers.router, prefix="/drivers", tags=["Drivers"])
app.include_router(pets.router, prefix="/pets", tags=["Pets"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(driver_locations.router, prefix="/driver_locations", tags=["Driver Locations"])
app.include_router(order_tracking.router, prefix="/order_tracking", tags=["Order Tracking"])
app.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
# app.include_router(live_tracking.router, prefix="/live_tracking", tags=["Live Tracking"])   
app.include_router(live_tracking.router, prefix="/ws", tags=["Live Tracking"])
app.include_router(driver_ws.router, prefix="/driver_ws", tags=["Driver WS"])   
app.include_router(auth.router, prefix="/auth", tags=["Auth"])   
app.include_router(pricing.router)   
app.include_router(settings.router, prefix="/settings", tags=["Settings"])   
app.include_router(payments.router, prefix="/payments", tags=["Payments"])
app.include_router(wallet.router)

app.include_router(chat_router)

@app.websocket("/ws/chat/{order_id}")
async def websocket_chat(
    websocket: WebSocket,
    order_id: int,
    user_id: int,
    role: str
):
    await chat_ws(websocket, order_id, user_id, role)

@app.get("/")
def read_root():
    return {"message": "Pet Transport API running"}

from app.models import PetType
from app.database import SessionLocal

def seed_pet_types():
    db = SessionLocal()
    try:
        if db.query(PetType).count() == 0:
            types = [
                {"name": "Dog", "icon": "🐶"},
                {"name": "Cat", "icon": "🐱"},
                {"name": "Other", "icon": "🐰"},
            ]
            for t in types:
                db_type = PetType(**t)
                db.add(db_type)
            db.commit()
            print("Seeded pet types")
    except Exception as e:
        print(f"Error seeding pet types: {e}")
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    seed_pet_types()
    asyncio.create_task(listen_chat())

# @app.websocket("/ws/driver/{driver_id}")
# async def driver_ws(websocket: WebSocket, driver_id: int):
#     await websocket.accept()
#     print(f"Driver {driver_id} connected")
#     try:
#         while True:
#             data = await websocket.receive_json()
#             print(f"Received from driver {driver_id}:", data)
#             await websocket.send_json(data)  # echo กลับ client
#     except Exception as e:
#         print(f"Driver {driver_id} disconnected:", e)
