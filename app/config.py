from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    google_maps_api_key: str
    here_maps_api_key: Optional[str] = None
    stripe_secret_key: str
    stripe_publishable_key: Optional[str] = None
    
    class Config:
        env_file = ".env"  # บอกให้ Pydantic โหลดค่า environment จาก .env
        extra = "forbid"

settings = Settings()
