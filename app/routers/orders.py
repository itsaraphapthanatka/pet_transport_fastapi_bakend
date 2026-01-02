from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, User, Driver, Pet, DeclinedOrder, DriverLocation
from app.schemas import OrderCreate, OrderOut, OrderUpdate, DeclinedOrderCreate
from app.core.security import get_current_user
from app.routers.settings import get_setting
import math

router = APIRouter()

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula. Returns distance in kilometers."""
    R = 6371  # Radius of Earth in kilometers
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = (math.sin(dLat / 2) * math.sin(dLat / 2) +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dLon / 2) * math.sin(dLon / 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.post("/", response_model=OrderOut)
def create_order(
    order: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order_data = order.dict()
    order_data['user_id'] = current_user.id
    
    # Get commission rate from database settings
    commission_rate_str = get_setting(db, "commission_rate", default="0.07")
    commission_rate = float(commission_rate_str)
    
    # Calculate commission and store the rate used
    if order_data.get('price'):
        price = float(order_data['price'])
        order_data['commission_rate'] = commission_rate
        order_data['platform_fee'] = round(price * commission_rate, 2)
        order_data['driver_earnings'] = round(price * (1 - commission_rate), 2)
    
    # Extract pet_ids
    pet_ids = order_data.pop('pet_ids', [])
    if not pet_ids and order_data.get('pet_id'):
        pet_ids = [order_data['pet_id']]

    db_order = Order(**order_data)
    
    # Set default payment values if not provided
    if not db_order.payment_method:
        db_order.payment_method = "cash"
    if not db_order.payment_status:
        db_order.payment_status = "pending"
        
    db.add(db_order)
    db.flush() # Flush to get ID

    # Add pets
    for pid in pet_ids:
        # Verify pet exists and belongs to user if needed (optional check)
        # Create relation
        if pid:
            from app.models import OrderPet # Local import to avoid circular dependency
            db_order_pet = OrderPet(order_id=db_order.id, pet_id=pid)
            db.add(db_order_pet)

    db.commit()
    db.refresh(db_order)
    return db_order

@router.get("/", response_model=list[OrderOut])
def list_orders(
    status: Optional[str] = None,
    driver_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Order).order_by(Order.created_at.desc())
    
    if status:
        query = query.filter(Order.status == status)
    
    if driver_id:
        query = query.filter(Order.driver_id == driver_id)
        return query.all() # No radius filter if specifically asking for a driver's orders

    # If driver (and no specific driver_id requested), apply filters for "available jobs"
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver:
        # If the driver is asking for their OWN history via this endpoint, we should allow it.
        # But usually, they call it without params for "available jobs".
        
        # If status is provided and it's NOT 'pending', it's likely a history view.
        if status and status != 'pending':
            query = query.filter(Order.driver_id == driver.id)
            return query.all()

        # Default behavior: Show available jobs (pending or already assigned to THEM)
        # 1. Hide declined orders
        declined_ids = db.query(DeclinedOrder.order_id).filter(DeclinedOrder.driver_id == driver.id).all()
        declined_ids = [r[0] for r in declined_ids]
        if declined_ids:
            query = query.filter(Order.id.notin_(declined_ids))
        
        # 2. Filter by work radius for PENDING orders
        # If status is 'pending' (or not provided, implying available jobs), we apply radius.
        if not status or status == 'pending':
            driver_location = db.query(DriverLocation).filter(DriverLocation.driver_id == driver.id).first()
            if driver_location and driver.work_radius_km:
                all_orders = query.all()
                filtered_orders = []
                for order in all_orders:
                    # If it's already accepted by THIS driver, include it regardless of current radius
                    if order.driver_id == driver.id:
                        filtered_orders.append(order)
                        continue
                        
                    # Otherwise check radius
                    distance = calculate_distance(
                        driver_location.lat,
                        driver_location.lng,
                        order.pickup_lat,
                        order.pickup_lng
                    )
                    if distance <= driver.work_radius_km:
                        filtered_orders.append(order)
                return filtered_orders
    else:
        # If customer, only show their own orders
        query = query.filter(Order.user_id == current_user.id)
            
    return query.all()

@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order

@router.post("/{order_id}/accept", response_model=OrderOut)
def accept_order(
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a driver
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can accept orders"
        )
    
    # Get the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
        
    # Assign driver to order
    if order.status == "accepted" and order.driver_id == driver.id:
        return order # Idempotent: already accepted by this driver

    # Check if order is pending
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not pending"
        )
        
    order.driver_id = driver.id
    order.status = "accepted"
    
    db.commit()
    db.refresh(order)
    
    return order
@router.patch("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Special handling for accepting an order
    if order_update.status == "accepted" or (order_update.driver_id is not None and db_order.status == "pending"):
        # Check if user is a driver
        driver_lookup = db.query(Driver).filter(Driver.user_id == current_user.id).first()
        if not driver_lookup:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only drivers can accept orders"
            )
        
        # Idempotency
        if db_order.status == "accepted" and db_order.driver_id == (order_update.driver_id or driver_lookup.id):
             pass # Already in correct state
        elif db_order.status != "pending":
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order is not pending (current: {db_order.status})"
            )
        else:
            db_order.driver_id = order_update.driver_id or driver_lookup.id
            db_order.status = "accepted"
    
    # Apply other updates
    update_data = order_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key not in ["status", "driver_id"]: # Handled above or explicitly
            setattr(db_order, key, value)
        elif key == "status" and value != "accepted": # If changing to something else like "cancelled"
             setattr(db_order, key, value)

    db.commit()
    db.refresh(db_order)
    return db_order
@router.post("/{order_id}/pickup", response_model=OrderOut)
def pickup_order(
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a driver
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can perform this action"
        )

    # Get the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if driver matches
    if order.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the driver for this order"
        )
        
    # Check status (Idempotent)
    if order.status == "in_progress":
        return order
    
    if order.status != "accepted":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in 'accepted' status to pickup (current: {order.status})"
        )
        
    # Update status
    order.status = "in_progress" # or picked_up based on convention, users usually prefer "in_progress" for ride
    
    db.commit()
    db.refresh(order)
    
    return order

@router.post("/{order_id}/complete", response_model=OrderOut)
def complete_order(
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if user is a driver
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can perform this action"
        )

    # Get the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if driver matches
    if order.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the driver for this order"
        )
        
    # Check status (Idempotent)
    if order.status == "completed":
        return order

    if order.status != "in_progress":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in 'in_progress' status to complete (current: {order.status})"
        )

    # Check if paid
    if order.payment_status != "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment required before completion"
        )
            
    # Update status
    order.status = "completed"
    
    db.commit()
    db.refresh(order)
    
    return order
@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Get the order
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # 1. Idempotency Check
    if order.status == "cancelled":
        return order

    # 2. Check if current user is the Customer (Order Owner)
    if order.user_id == current_user.id:
        order.status = "cancelled"
        # When a customer cancels, we also unassign the driver if any
        order.driver_id = None
        db.commit()
        db.refresh(order)
        return order

    # 3. Check if current user is the Assigned Driver
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if driver and order.driver_id == driver.id:
        # Driver is "releasing" the order back to the pool
        if order.status == "pending" and order.driver_id is None:
            return order # Already released
            
        order.driver_id = None
        order.status = "pending"
        db.commit()
        db.refresh(order)
        return order

    # 4. Unauthorized
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the customer or the assigned driver can cancel/release this order"
    )

@router.post("/{order_id}/decline")
def decline_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=403, detail="Only drivers can decline orders")
    
    # Idempotent decline
    exists = db.query(DeclinedOrder).filter(
        DeclinedOrder.driver_id == driver.id,
        DeclinedOrder.order_id == order_id
    ).first()
    
    if not exists:
        db_decline = DeclinedOrder(driver_id=driver.id, order_id=order_id)
        db.add(db_decline)
        db.commit()
        
    return {"message": "Order declined successfully"}
@router.post("/{order_id}/pay-wallet", response_model=OrderOut)
def pay_with_wallet(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your order")
        
    if order.payment_status == "paid":
        return order
        
    if current_user.wallet_balance < order.price:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance")
        
    # Deduct balance
    current_user.wallet_balance -= order.price
    
    # Update order
    order.payment_status = "paid"
    order.payment_method = "wallet"
    
    # Create Wallet Transaction
    from app.models import WalletTransaction
    txn = WalletTransaction(
        user_id=current_user.id,
        amount=-order.price,
        type="payment",
        status="success",
        reference_id=str(order.id),
        description=f"Payment for trip #{order.id}"
    )
    db.add(txn)
    
    # Update platform/driver earnings if needed (simulated for now)
    # In a real app, you'd also credit the driver's wallet here (minus commission)
    if order.driver_id:
        driver = db.query(Driver).filter(Driver.id == order.driver_id).first()
        if driver:
            driver_user = db.query(User).filter(User.id == driver.user_id).first()
            if driver_user:
                driver_user.wallet_balance += order.driver_earnings
                driver_txn = WalletTransaction(
                    user_id=driver_user.id,
                    amount=order.driver_earnings,
                    type="earning",
                    status="success",
                    reference_id=str(order.id),
                    description=f"Earnings from trip #{order.id}"
                )
                db.add(driver_txn)
    
    db.commit()
    db.refresh(order)
    return order
