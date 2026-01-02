from sqlalchemy import create_engine, text
import sys

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:5433/pet_transport"

try:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, status, created_at FROM orders ORDER BY id DESC LIMIT 5"))
        orders = result.fetchall()
        print("Recent Orders in DB:")
        for o in orders:
            created_at_val = o.created_at
            print(f"ID: {o.id}, Status: {o.status}, CreatedAt: {created_at_val} (Type: {type(created_at_val)})")
            
except Exception as e:
    print(f"ERROR: {str(e)}")
