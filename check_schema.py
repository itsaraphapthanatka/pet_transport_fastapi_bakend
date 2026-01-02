import requests

# Assuming the backend is running on localhost:8000
API_URL = "http://127.0.0.1:8000"

# We need a token. Let's try to login as a user first.
# If we can't login easily in a script, we might have to assume the user can check the network tab.
# But let's try to simulate a login if we have a test user.
# For now, let's just inspect the schema file essentially, or unit test the Pydantic model serialization.

from app.schemas import OrderOut
from app.models import Order, User
from datetime import datetime

# Unit test style check
def test_schema_serialization():
    dummy_user = User(id=1, full_name="Test User", email="test@test.com", wallet_balance=0)
    
    dummy_order = Order(
        id=123,
        user_id=1,
        pet_id=1,
        pickup_address="A", pickup_lat=0, pickup_lng=0,
        dropoff_address="B", dropoff_lat=0, dropoff_lng=0,
        created_at=datetime.utcnow(),
        customer=dummy_user
    )
    
    # Manually attach customer for Pydantic 'from_attributes'
    dummy_order.customer = dummy_user
    
    try:
        model = OrderOut.from_orm(dummy_order)
        print("Serialization Successful!")
        print(f"created_at in model: {model.created_at}")
        print(f"JSON Output: {model.json()}")
    except Exception as e:
        print(f"Serialization Failed: {e}")

if __name__ == "__main__":
    test_schema_serialization()
