from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.core.security import get_current_user
from app.config import settings
import stripe

stripe.api_key = settings.stripe_secret_key

router = APIRouter()

def get_or_create_stripe_customer(user: models.User, db: Session):
    try:
        if user.stripe_customer_id:
            return user.stripe_customer_id
        
        customer = stripe.Customer.create(
            email=user.email,
            name=user.full_name,
            metadata={"user_id": user.id}
        )
        user.stripe_customer_id = customer.id
        db.commit()
        return customer.id
    except Exception as e:
        print(f"Error in get_or_create_stripe_customer: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Stripe Customer Error: {str(e)}")

@router.get("/payment-methods", response_model=List[schemas.PaymentMethodOut])
def list_payment_methods(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        customer_id = get_or_create_stripe_customer(current_user, db)
        payment_methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card",
        )
        
        print(f"DEBUG: Found {len(payment_methods.data)} payment methods for customer {customer_id}")
        results = []
        for pm in payment_methods.data:
            results.append({
                "id": pm.id,
                "brand": pm.card.brand if pm.card else None,
                "last4": pm.card.last4 if pm.card else None,
                "exp_month": pm.card.exp_month if pm.card else None,
                "exp_year": pm.card.exp_year if pm.card else None
            })
        print(f"DEBUG: Returning results: {results}")
        return results
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error listing payment methods: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/", response_model=schemas.PaymentOut)
def create_payment(payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    # Verify order exists
    order = db.query(models.Order).filter(models.Order.id == payment.order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_payment = models.Payment(**payment.dict())
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    
    # Update order payment status if it's cash or successfully simulated
    if payment.method == "cash":
        order.payment_status = "pending"
        order.payment_method = "cash"
    else:
        # For non-cash, we might wait for verification, but for now let's set it based on payment status
        order.payment_status = payment.status
        order.payment_method = payment.method
    
    db.commit()
    return db_payment

@router.get("/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return db_payment

@router.post("/{payment_id}/verify", response_model=schemas.PaymentOut)
def verify_payment(payment_id: int, status: str, transaction_id: str = None, db: Session = Depends(get_db)):
    db_payment = db.query(models.Payment).filter(models.Payment.id == payment_id).first()
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    db_payment.status = status
    if transaction_id:
        db_payment.transaction_id = transaction_id
    
    # Update associated order
    order = db.query(models.Order).filter(models.Order.id == db_payment.order_id).first()
    if order:
        if status == "successful":
            order.payment_status = "paid"
        elif status == "failed":
            order.payment_status = "failed"
    
    db.commit()
    db.refresh(db_payment)
    return db_payment
@router.get("/order/{order_id}", response_model=schemas.PaymentOut)
def get_payment_by_order_id(order_id: int, db: Session = Depends(get_db)):
    db_payment = db.query(models.Payment).filter(models.Payment.order_id == order_id).first()
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    return db_payment

@router.post("/create-payment-intent")
def create_payment_intent(payment_data: schemas.PaymentCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        customer_id = get_or_create_stripe_customer(current_user, db)
        
        # Create an Ephemeral Key for the Payment Sheet
        ephemeralKey = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version='2022-11-15',
        )
        
        # Stripe expects amount in subunits (e.g., cents/satang), so multiply by 100 for THB
        payment_intent = stripe.PaymentIntent.create(
            amount=int(payment_data.amount * 100),
            currency='thb',
            customer=customer_id,
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'order_id': payment_data.order_id,
                'user_id': current_user.id
            }
        )
        
        return {
            'paymentIntent': payment_intent.client_secret,
            'ephemeralKey': ephemeralKey.secret,
            'customer': customer_id,
            'publishableKey': settings.stripe_publishable_key
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/setup-intent", response_model=schemas.SetupIntentResponse)
def create_setup_intent(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        customer_id = get_or_create_stripe_customer(current_user, db)
        
        ephemeralKey = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version='2022-11-15',
        )
        
        setup_intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=['card']
        )
        
        return {
            'setupIntent': setup_intent.client_secret,
            'ephemeralKey': ephemeralKey.secret,
            'customer': customer_id,
            'publishableKey': settings.stripe_publishable_key
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/payment-methods/{pm_id}")
def detach_payment_method(pm_id: str, current_user: models.User = Depends(get_current_user)):
    try:
        # Verify PM belongs to user's customer
        pm = stripe.PaymentMethod.retrieve(pm_id)
        if pm.customer != current_user.stripe_customer_id:
            raise HTTPException(status_code=403, detail="Not authorized to detach this payment method")
            
        stripe.PaymentMethod.detach(pm_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
