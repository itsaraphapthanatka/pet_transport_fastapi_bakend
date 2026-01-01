"""
Migration script to calculate and update commission for existing orders
Run this once to update all existing orders with platform_fee and driver_earnings
"""
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Order

def update_existing_orders_commission():
    """Calculate and update commission for all existing orders"""
    db: Session = SessionLocal()
    
    try:
        # Get all orders that have a price but missing commission data
        orders = db.query(Order).filter(
            Order.price.isnot(None),
            Order.platform_fee.is_(None)
        ).all()
        
        updated_count = 0
        
        for order in orders:
            # Calculate commission (7% for platform, 93% for driver)
            price = float(order.price)
            order.platform_fee = round(price * 0.07, 2)
            order.driver_earnings = round(price * 0.93, 2)
            updated_count += 1
            
            print(f"Order #{order.id}: Price ฿{price:.2f} -> Platform Fee ฿{order.platform_fee:.2f}, Driver Earnings ฿{order.driver_earnings:.2f}")
        
        # Commit all changes
        db.commit()
        print(f"\n✅ Successfully updated {updated_count} orders with commission data")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating orders: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting commission migration for existing orders...")
    print("=" * 60)
    update_existing_orders_commission()
    print("=" * 60)
    print("Migration completed!")
