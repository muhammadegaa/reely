"""
Stripe payment integration for Reely subscriptions
"""
import os
import stripe
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Subscription, SubscriptionTier
from auth import get_current_active_user
from dotenv import load_dotenv

load_dotenv()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Price IDs from Stripe Dashboard
STRIPE_PRICES = {
    SubscriptionTier.PRO: os.getenv("STRIPE_PRICE_ID_PRO"),
    SubscriptionTier.PREMIUM: os.getenv("STRIPE_PRICE_ID_PREMIUM")
}

router = APIRouter(prefix="/payments", tags=["Payments"])

# Pydantic models
class SubscriptionRequest(BaseModel):
    tier: str  # "pro" or "premium"
    success_url: str
    cancel_url: str

class SubscriptionResponse(BaseModel):
    checkout_url: str
    session_id: str

class PortalRequest(BaseModel):
    return_url: str

class PortalResponse(BaseModel):
    portal_url: str

@router.post("/create-checkout", response_model=SubscriptionResponse)
async def create_checkout_session(
    request: SubscriptionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe checkout session for subscription"""
    
    # Validate subscription tier
    if request.tier not in ["pro", "premium"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid subscription tier. Must be 'pro' or 'premium'"
        )
    
    tier = SubscriptionTier(request.tier)
    price_id = STRIPE_PRICES.get(tier)
    
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe price ID not configured for this tier"
        )
    
    try:
        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={
                    "user_id": str(current_user.id)
                }
            )
            current_user.stripe_customer_id = customer.id
            db.commit()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=current_user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": str(current_user.id),
                "tier": request.tier
            }
        )
        
        return SubscriptionResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id
        )
        
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

@router.post("/create-portal", response_model=PortalResponse)
async def create_customer_portal(
    request: PortalRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Create a Stripe customer portal session for managing subscription"""
    
    if not current_user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer found. Please subscribe first."
        )
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=request.return_url
        )
        
        return PortalResponse(portal_url=portal_session.url)
        
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stripe error: {str(e)}"
        )

@router.get("/subscription-status")
async def get_subscription_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current subscription status"""
    
    if not current_user.stripe_customer_id:
        return {
            "has_subscription": False,
            "tier": SubscriptionTier.FREE.value,
            "status": "inactive"
        }
    
    # Get active subscription from database
    active_subscription = db.query(Subscription).filter(
        Subscription.user_id == current_user.id,
        Subscription.status.in_(["active", "trialing"])
    ).first()
    
    if not active_subscription:
        return {
            "has_subscription": False,
            "tier": SubscriptionTier.FREE.value,
            "status": "inactive"
        }
    
    return {
        "has_subscription": True,
        "tier": active_subscription.tier,
        "status": active_subscription.status,
        "current_period_start": active_subscription.current_period_start,
        "current_period_end": active_subscription.current_period_end
    }

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events"""
    
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle different event types
    if event['type'] == 'checkout.session.completed':
        await handle_checkout_session_completed(event['data']['object'], db)
    elif event['type'] == 'customer.subscription.updated':
        await handle_subscription_updated(event['data']['object'], db)
    elif event['type'] == 'customer.subscription.deleted':
        await handle_subscription_deleted(event['data']['object'], db)
    elif event['type'] == 'invoice.payment_succeeded':
        await handle_payment_succeeded(event['data']['object'], db)
    elif event['type'] == 'invoice.payment_failed':
        await handle_payment_failed(event['data']['object'], db)
    
    return {"status": "success"}

async def handle_checkout_session_completed(session: Dict[str, Any], db: Session):
    """Handle completed checkout session"""
    user_id = int(session['metadata']['user_id'])
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        print(f"User not found for checkout session: {user_id}")
        return
    
    # Get the subscription from Stripe
    subscription = stripe.Subscription.retrieve(session['subscription'])
    
    # Update user's subscription tier
    tier = session['metadata'].get('tier', 'pro')
    user.subscription_tier = tier
    
    # Create or update subscription record
    db_subscription = Subscription(
        user_id=user.id,
        stripe_subscription_id=subscription.id,
        tier=tier,
        status=subscription.status,
        current_period_start=datetime.fromtimestamp(subscription.current_period_start, timezone.utc),
        current_period_end=datetime.fromtimestamp(subscription.current_period_end, timezone.utc)
    )
    
    db.add(db_subscription)
    db.commit()
    
    print(f"Subscription created for user {user.email}: {tier}")

async def handle_subscription_updated(subscription: Dict[str, Any], db: Session):
    """Handle subscription updates"""
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = subscription['status']
        db_subscription.current_period_start = datetime.fromtimestamp(
            subscription['current_period_start'], timezone.utc
        )
        db_subscription.current_period_end = datetime.fromtimestamp(
            subscription['current_period_end'], timezone.utc
        )
        
        # Update user's subscription tier if changed
        user = db.query(User).filter(User.id == db_subscription.user_id).first()
        if user:
            if subscription['status'] in ['active', 'trialing']:
                user.subscription_tier = db_subscription.tier
            else:
                user.subscription_tier = SubscriptionTier.FREE.value
        
        db.commit()
        print(f"Subscription updated: {subscription['id']} -> {subscription['status']}")

async def handle_subscription_deleted(subscription: Dict[str, Any], db: Session):
    """Handle subscription cancellation"""
    db_subscription = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == subscription['id']
    ).first()
    
    if db_subscription:
        db_subscription.status = 'canceled'
        
        # Downgrade user to free tier
        user = db.query(User).filter(User.id == db_subscription.user_id).first()
        if user:
            user.subscription_tier = SubscriptionTier.FREE.value
        
        db.commit()
        print(f"Subscription canceled: {subscription['id']}")

async def handle_payment_succeeded(invoice: Dict[str, Any], db: Session):
    """Handle successful payment"""
    # This is called for recurring payments
    print(f"Payment succeeded for invoice: {invoice['id']}")
    # You could log this or send confirmation emails here

async def handle_payment_failed(invoice: Dict[str, Any], db: Session):
    """Handle failed payment"""
    print(f"Payment failed for invoice: {invoice['id']}")
    # You could send notification emails or take other actions here

def check_subscription_access(user: User, required_features: list) -> bool:
    """Check if user's subscription tier includes required features"""
    from models import SUBSCRIPTION_LIMITS
    
    tier = SubscriptionTier(user.subscription_tier)
    available_features = SUBSCRIPTION_LIMITS[tier]["features"]
    
    return all(feature in available_features for feature in required_features)