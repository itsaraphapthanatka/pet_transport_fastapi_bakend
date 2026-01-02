from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import models, schemas
from app.core.security import get_current_user
from app.config import settings
from app.routers.payments import get_or_create_stripe_customer
import stripe

stripe.api_key = settings.stripe_secret_key

router = APIRouter(
    prefix="/wallet",
    tags=["wallet"]
)

@router.get("/balance", response_model=schemas.UserOut)
def get_balance(current_user: models.User = Depends(get_current_user)):
    return current_user

@router.get("/transactions", response_model=List[schemas.WalletTransactionOut])
def get_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    transactions = db.query(models.WalletTransaction)\
        .filter(models.WalletTransaction.user_id == current_user.id)\
        .order_by(models.WalletTransaction.created_at.desc())\
        .all()
    return transactions

@router.post("/topup", response_model=schemas.TopupIntentResponse)
def create_topup_intent(
    request: schemas.WalletTopupRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    try:
        customer_id = get_or_create_stripe_customer(current_user, db)
        
        # Create an Ephemeral Key
        ephemeralKey = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version='2022-11-15',
        )
        
        # Create a PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=int(request.amount * 100),
            currency='thb',
            customer=customer_id,
            automatic_payment_methods={
                'enabled': True,
            },
            metadata={
                'type': 'wallet_topup',
                'user_id': current_user.id,
                'amount': float(request.amount)
            }
        )
        
        # Create a pending transaction
        new_txn = models.WalletTransaction(
            user_id=current_user.id,
            amount=request.amount,
            type="topup",
            status="pending",
            description=f"Top-up via {request.method}",
            reference_id=payment_intent.id
        )
        
        db.add(new_txn)
        db.commit()
        db.refresh(new_txn)
        
        return {
            'paymentIntent': payment_intent.client_secret,
            'ephemeralKey': ephemeralKey.secret,
            'customer': customer_id,
            'publishableKey': settings.stripe_publishable_key,
            'transaction_id': new_txn.id
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-topup/{transaction_id}", response_model=schemas.WalletTransactionOut)
def verify_topup(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    txn = db.query(models.WalletTransaction).filter(
        models.WalletTransaction.id == transaction_id,
        models.WalletTransaction.user_id == current_user.id
    ).first()
    
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    if txn.status == "success":
        return txn
        
    try:
        # Check PaymentIntent status from Stripe
        intent = stripe.PaymentIntent.retrieve(txn.reference_id)
        
        if intent.status == "succeeded":
            # Avoid duplicate updates
            if txn.status != "success":
                txn.status = "success"
                current_user.wallet_balance += txn.amount
                db.commit()
                db.refresh(txn)
        elif intent.status == "canceled":
            txn.status = "failed"
            db.commit()
            
        return txn
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
