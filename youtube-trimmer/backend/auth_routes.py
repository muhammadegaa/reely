"""
Authentication routes for Reely - User registration, login, and token management
"""
import re
from typing import Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, validator

from database import get_db
from models import User, APIKey, get_or_create_usage_stats, SUBSCRIPTION_LIMITS, SubscriptionTier
from auth import (
    get_password_hash, authenticate_user, create_token_pair, 
    refresh_access_token, get_current_user, get_current_active_user,
    create_api_key, revoke_api_key, validate_user_permissions
)
from config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])

# Request/Response Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Za-z]', v):
            raise ValueError('Password must contain at least one letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    subscription_tier: str
    is_verified: bool
    created_at: datetime
    usage_stats: dict

class APIKeyRequest(BaseModel):
    name: str
    expires_in_days: Optional[int] = 365

class APIKeyResponse(BaseModel):
    id: int
    api_key: Optional[str] = None  # Only included when creating
    name: str
    preview: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool

# Authentication endpoints
@router.post("/register", response_model=TokenResponse)
async def register_user(
    user_data: UserRegistration,
    background_tasks: BackgroundTasks,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user account"""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        subscription_tier=SubscriptionTier.FREE.value,
        last_login=datetime.now(timezone.utc)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create initial usage stats
    get_or_create_usage_stats(db, new_user.id)
    
    # Generate tokens
    token_data = create_token_pair({"sub": new_user.email})
    
    # Add user info to response
    user_info = {
        "id": new_user.id,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "subscription_tier": new_user.subscription_tier,
        "is_verified": new_user.is_verified
    }
    
    # Background tasks (e.g., send welcome email)
    background_tasks.add_task(send_welcome_email, new_user.email)
    
    return TokenResponse(
        **token_data,
        user=user_info
    )

@router.post("/login", response_model=TokenResponse)
async def login_user(
    user_credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return tokens"""
    
    # Get client IP for rate limiting
    client_ip = request.client.host
    
    # Authenticate user
    user = authenticate_user(db, user_credentials.email, user_credentials.password, client_ip)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    # Generate tokens
    token_data = create_token_pair({"sub": user.email})
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    # Get usage stats for current month
    usage_stats = get_or_create_usage_stats(db, user.id)
    limits = SUBSCRIPTION_LIMITS.get(user.subscription_tier, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE])
    
    user_info = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "subscription_tier": user.subscription_tier,
        "is_verified": user.is_verified,
        "usage_stats": {
            "trims_used": usage_stats.trims_count,
            "hooks_used": usage_stats.hooks_count,
            "trims_limit": limits["monthly_trims"],
            "hooks_limit": limits["monthly_hooks"]
        }
    }
    
    return TokenResponse(
        **token_data,
        user=user_info
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    try:
        token_data = refresh_access_token(refresh_request.refresh_token, db)
        
        # Get user info
        from auth import verify_token
        email = verify_token(refresh_request.refresh_token, "refresh")
        user = db.query(User).filter(User.email == email).first()
        
        user_info = {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "subscription_tier": user.subscription_tier,
            "is_verified": user.is_verified
        }
        
        return TokenResponse(
            **token_data,
            user=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

@router.post("/logout")
async def logout_user(
    current_user: User = Depends(get_current_active_user)
):
    """Logout user (client should discard tokens)"""
    # In a more sophisticated setup, you'd invalidate the token in Redis
    return {"message": "Successfully logged out"}

# User profile endpoints
@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's profile information"""
    
    # Get current month usage stats
    usage_stats = get_or_create_usage_stats(db, current_user.id)
    limits = SUBSCRIPTION_LIMITS.get(current_user.subscription_tier, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE])
    
    usage_info = {
        "current_month": {
            "trims_used": usage_stats.trims_count,
            "hooks_used": usage_stats.hooks_count,
            "api_requests": usage_stats.api_requests_count
        },
        "limits": {
            "monthly_trims": limits["monthly_trims"],
            "monthly_hooks": limits["monthly_hooks"],
            "max_video_duration": limits["max_video_duration"],
            "features": limits["features"]
        },
        "subscription": {
            "tier": current_user.subscription_tier,
            "can_upgrade": current_user.subscription_tier != SubscriptionTier.PREMIUM.value
        }
    }
    
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        subscription_tier=current_user.subscription_tier,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at,
        usage_stats=usage_info
    )

# API Key management
@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's API keys"""
    
    if not validate_user_permissions(current_user, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access requires Pro or Premium subscription"
        )
    
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).all()
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            preview=key.key_preview,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            is_active=key.is_active
        )
        for key in api_keys
    ]

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_user_api_key(
    key_request: APIKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key"""
    
    # Check API key limit
    existing_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()
    
    if existing_keys >= settings.max_api_keys_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum of {settings.max_api_keys_per_user} active API keys allowed"
        )
    
    api_key_data = create_api_key(
        current_user, 
        key_request.name, 
        db, 
        key_request.expires_in_days
    )
    
    return APIKeyResponse(**api_key_data)

@router.delete("/api-keys/{key_id}")
async def revoke_user_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    
    success = revoke_api_key(key_id, current_user, db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {"message": "API key revoked successfully"}

# Background tasks
async def send_welcome_email(email: str):
    """Send welcome email to new user (placeholder)"""
    # Implement email sending logic here
    pass

# Utility endpoints
@router.get("/check-email/{email}")
async def check_email_availability(
    email: str,
    db: Session = Depends(get_db)
):
    """Check if email is available for registration"""
    
    existing_user = db.query(User).filter(User.email == email).first()
    return {"available": existing_user is None}

@router.get("/subscription-info")
async def get_subscription_info():
    """Get subscription tier information"""
    from config import get_subscription_config
    return get_subscription_config()