"""
User management routes for Reely
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from database import get_db
from models import User, SubscriptionTier, UsageLog
from auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    get_current_active_user,
    verify_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Pydantic models for API
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    subscription_tier: str
    monthly_trim_count: int
    monthly_hook_count: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

class TokenRefresh(BaseModel):
    refresh_token: str

class PasswordChange(BaseModel):
    current_password: str
    new_password: str

class UsageStats(BaseModel):
    monthly_trims_used: int
    monthly_hooks_used: int
    monthly_trims_limit: int
    monthly_hooks_limit: int
    subscription_tier: str
    days_until_reset: int

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        subscription_tier=SubscriptionTier.FREE.value,
        last_usage_reset=datetime.now(timezone.utc)
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create tokens
    access_token = create_access_token(data={"sub": db_user.email})
    refresh_token = create_refresh_token(data={"sub": db_user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(db_user)
    )

@router.post("/login", response_model=Token)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return JWT tokens"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is deactivated"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user)
    )

@router.post("/refresh", response_model=dict)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    """Refresh access token using refresh token"""
    email = verify_token(token_data.refresh_token, "refresh")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    access_token = create_access_token(data={"sub": email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.model_validate(current_user)

@router.put("/me", response_model=UserResponse)
async def update_current_user(
    full_name: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information"""
    if full_name is not None:
        current_user.full_name = full_name
    
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.model_validate(current_user)

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    from auth import verify_password
    
    # Verify current password
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Password updated successfully"}

@router.get("/usage", response_model=UsageStats)
async def get_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's current usage statistics"""
    from models import SUBSCRIPTION_LIMITS
    
    # Check if we need to reset monthly usage
    now = datetime.now(timezone.utc)
    if current_user.last_usage_reset.month != now.month or current_user.last_usage_reset.year != now.year:
        current_user.monthly_trim_count = 0
        current_user.monthly_hook_count = 0
        current_user.last_usage_reset = now
        db.commit()
        db.refresh(current_user)
    
    # Get subscription limits
    limits = SUBSCRIPTION_LIMITS[SubscriptionTier(current_user.subscription_tier)]
    
    # Calculate days until next reset
    next_month = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
    days_until_reset = (next_month - now).days
    
    return UsageStats(
        monthly_trims_used=current_user.monthly_trim_count,
        monthly_hooks_used=current_user.monthly_hook_count,
        monthly_trims_limit=limits["monthly_trims"],
        monthly_hooks_limit=limits["monthly_hooks"],
        subscription_tier=current_user.subscription_tier,
        days_until_reset=days_until_reset
    )

@router.delete("/me")
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user account"""
    # In a real application, you might want to:
    # 1. Cancel any active subscriptions
    # 2. Delete user data from cloud storage
    # 3. Log the deletion for audit purposes
    
    # For now, we'll just deactivate the account
    current_user.is_active = False
    current_user.updated_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Account deactivated successfully"}

def check_user_limits(user: User, action_type: str, db: Session) -> bool:
    """Check if user can perform an action based on their subscription limits"""
    from models import SUBSCRIPTION_LIMITS
    
    # Reset monthly usage if needed
    now = datetime.now(timezone.utc)
    if user.last_usage_reset.month != now.month or user.last_usage_reset.year != now.year:
        user.monthly_trim_count = 0
        user.monthly_hook_count = 0
        user.last_usage_reset = now
        db.commit()
    
    limits = SUBSCRIPTION_LIMITS[SubscriptionTier(user.subscription_tier)]
    
    if action_type == "trim":
        limit = limits["monthly_trims"]
        current = user.monthly_trim_count
    elif action_type == "hook_detection":
        limit = limits["monthly_hooks"]
        current = user.monthly_hook_count
    else:
        return True  # Unknown action, allow by default
    
    # -1 means unlimited
    if limit == -1:
        return True
    
    return current < limit

def increment_usage(user: User, action_type: str, db: Session, credits_used: int = 1):
    """Increment user's usage count and log the action"""
    # Update usage counts
    if action_type == "trim":
        user.monthly_trim_count += credits_used
    elif action_type == "hook_detection":
        user.monthly_hook_count += credits_used
    
    # Log the usage
    usage_log = UsageLog(
        user_id=user.id,
        action_type=action_type,
        credits_used=credits_used
    )
    
    db.add(usage_log)
    db.commit()