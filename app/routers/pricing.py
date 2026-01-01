from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx
from app.config import settings
from app.database import get_db
from app.models import Settings as SettingsModel
from app.schemas import SettingsOut

router = APIRouter(prefix="/pricing", tags=["Pricing"])

# ==============================
# API KEYS
# ==============================
GOOGLE_MAPS_API_KEY = settings.google_maps_api_key
HERE_MAPS_API_KEY = settings.here_maps_api_key

# ==============================
# PRICING CONFIG
# ==============================
PRICING_RATES = {
    "car": {"base": 60, "per_km": 12, "per_min": 2, "min": 80},
    "suv": {"base": 80, "per_km": 15, "per_min": 3, "min": 120},
    "van": {"base": 120, "per_km": 18, "per_min": 4, "min": 200},
}

# ==============================
# MODELS
# ==============================
class EstimateRequest(BaseModel):
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    pet_weight_kg: int
    vehicle_type: str = "car"
    provider: str = "here"  # google | here


class EstimateResponse(BaseModel):
    distance_km: float
    duration_min: float
    estimated_price: int


class VehicleTypeInfo(BaseModel):
    key: str
    name: str
    rates: dict


# ==============================
# VEHICLE TYPES
# ==============================
@router.get("/vehicle-types", response_model=list[VehicleTypeInfo])
def get_vehicle_types():
    return [
        {"key": k, "name": k.upper(), "rates": v}
        for k, v in PRICING_RATES.items()
    ]


# ==============================
# DISTANCE SERVICE
# ==============================
async def get_distance_duration(
    pickup_lat: float,
    pickup_lng: float,
    dropoff_lat: float,
    dropoff_lng: float,
    provider: str
):
    # ---------- GOOGLE MAPS ----------
    if provider == "google":
        if not GOOGLE_MAPS_API_KEY:
            raise HTTPException(500, "Google Maps API Key not configured")

        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": f"{pickup_lat},{pickup_lng}",
            "destinations": f"{dropoff_lat},{dropoff_lng}",
            "key": GOOGLE_MAPS_API_KEY
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(url, params=params)
            data = res.json()

        if data.get("status") != "OK":
            raise HTTPException(400, "Google Maps API error")

        try:
            element = data["rows"][0]["elements"][0]
            if element["status"] != "OK":
                raise HTTPException(400, "Route not found")

            return (
                element["distance"]["value"],   # meters
                element["duration"]["value"]    # seconds
            )
        except (KeyError, IndexError):
            raise HTTPException(400, "Invalid Google Maps response")

    # ---------- HERE MAPS ----------
    if provider == "here":
        if not HERE_MAPS_API_KEY:
            raise HTTPException(500, "HERE Maps API Key not configured")

        url = "https://router.hereapi.com/v8/routes"
        params = {
            "transportMode": "car",
            "origin": f"{pickup_lat},{pickup_lng}",
            "destination": f"{dropoff_lat},{dropoff_lng}",
            "return": "summary",
            "apikey": HERE_MAPS_API_KEY
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(url, params=params)
            data = res.json()

        try:
            summary = data["routes"][0]["sections"][0]["summary"]
            return (
                summary["length"],    # meters
                summary["duration"]   # seconds
            )
        except (KeyError, IndexError):
            raise HTTPException(400, "HERE Maps API error")

    raise HTTPException(400, "Invalid provider (google | here)")


# ==============================
# ESTIMATE PRICE
# ==============================
@router.post("/estimate", response_model=EstimateResponse)
async def estimate_price(request: EstimateRequest, db: Session = Depends(get_db)):
    # Get provider from settings
    setting = db.query(SettingsModel).first()
    if not setting:
        setting = SettingsModel(map="here")
        db.add(setting)
        db.commit()
        db.refresh(setting)
    
    provider = setting.map if setting else request.provider.lower()

    distance_meters, duration_seconds = await get_distance_duration(
        pickup_lat=request.pickup_lat,
        pickup_lng=request.pickup_lng,
        dropoff_lat=request.dropoff_lat,
        dropoff_lng=request.dropoff_lng,
        provider=provider
    )

    distance_km = distance_meters / 1000
    duration_min = duration_seconds / 60

    # pricing
    v_type = request.vehicle_type.lower()
    rates = PRICING_RATES.get(v_type, PRICING_RATES["car"])

    base_fare = rates["base"]
    distance_cost = distance_km * rates["per_km"]
    time_cost = duration_min * rates["per_min"]
    
    # Weight-based surcharge
    # 0-10kg: no charge
    # 11-20kg: +20 THB
    # 21-30kg: +40 THB
    # 30kg+: +60 THB
    weight_surcharge = 0
    if request.pet_weight_kg > 30:
        weight_surcharge = 60
    elif request.pet_weight_kg > 20:
        weight_surcharge = 40
    elif request.pet_weight_kg > 10:
        weight_surcharge = 20

    total_price = base_fare + distance_cost + time_cost + weight_surcharge
    final_price = max(rates["min"], int(total_price))

    return EstimateResponse(
        distance_km=round(distance_km, 1),
        duration_min=round(duration_min, 0),
        estimated_price=final_price
    )

@router.get("/settings", response_model=SettingsOut)
def get_settings(db: Session = Depends(get_db)):
    setting = db.query(SettingsModel).first()
    if not setting:
        # Create default if not exists
        setting = SettingsModel(map="here")
        db.add(setting)
        db.commit()
        db.refresh(setting)
    return setting