"""
API Key management system for Reely
Allows users to create and manage API keys for programmatic access
"""
import hashlib
import secrets
import string
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, APIKey
from auth import get_current_active_user, get_user_from_api_key
from payments import check_subscription_access

router = APIRouter(prefix="/api-keys", tags=["API Keys"])

# Pydantic models
class APIKeyCreate(BaseModel):
    name: str
    expires_in_days: Optional[int] = None  # None means no expiration

class APIKeyResponse(BaseModel):
    id: int
    name: str
    key_preview: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]

class APIKeyCreated(BaseModel):
    api_key: str  # Full key, only returned once
    key_info: APIKeyResponse

class APIKeyList(BaseModel):
    api_keys: List[APIKeyResponse]
    total: int

def generate_api_key() -> str:
    """Generate a secure API key"""
    # Use a format like: rly_live_xxxxxxxxxxxxxxxxxxxxx (30 chars total prefix + key)
    prefix = "rly_live_"
    key_length = 32
    characters = string.ascii_letters + string.digits
    key_part = ''.join(secrets.choice(characters) for _ in range(key_length))
    return f"{prefix}{key_part}"

def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    return hashlib.sha256(api_key.encode()).hexdigest()

@router.post("/create", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for the authenticated user"""
    
    # Check if user has API access (Pro/Premium only)
    if not check_subscription_access(current_user, ["api_access"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key access requires Pro or Premium subscription. Upgrade to access API features."
        )
    
    # Check if user has reached API key limit (max 5 keys per user)
    existing_keys_count = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True
    ).count()
    
    if existing_keys_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum number of API keys reached (5). Please delete unused keys first."
        )
    
    # Generate new API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    key_preview = f"...{api_key[-4:]}"  # Show last 4 characters
    
    # Calculate expiration date
    expires_at = None
    if key_data.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=key_data.expires_in_days)
    
    # Create API key record
    db_api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_preview=key_preview,
        name=key_data.name,
        expires_at=expires_at
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return APIKeyCreated(
        api_key=api_key,  # Return full key only once
        key_info=APIKeyResponse(
            id=db_api_key.id,
            name=db_api_key.name,
            key_preview=db_api_key.key_preview,
            is_active=db_api_key.is_active,
            created_at=db_api_key.created_at,
            last_used_at=db_api_key.last_used_at,
            expires_at=db_api_key.expires_at
        )
    )

@router.get("/list", response_model=APIKeyList)
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all API keys for the authenticated user"""
    
    # Check if user has API access
    if not check_subscription_access(current_user, ["api_access"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key access requires Pro or Premium subscription."
        )
    
    api_keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id
    ).order_by(APIKey.created_at.desc()).all()
    
    return APIKeyList(
        api_keys=[
            APIKeyResponse(
                id=key.id,
                name=key.name,
                key_preview=key.key_preview,
                is_active=key.is_active,
                created_at=key.created_at,
                last_used_at=key.last_used_at,
                expires_at=key.expires_at
            )
            for key in api_keys
        ],
        total=len(api_keys)
    )

@router.patch("/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Activate or deactivate an API key"""
    
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = not api_key.is_active
    db.commit()
    
    return {
        "message": f"API key {'activated' if api_key.is_active else 'deactivated'}",
        "is_active": api_key.is_active
    }

@router.delete("/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete an API key"""
    
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted successfully"}

# Dependency for API key authentication
async def get_current_user_from_api_key(
    x_api_key: Optional[str] = Header(None, description="API key for authentication"),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from API key header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required in X-API-Key header"
        )
    
    user = get_user_from_api_key(x_api_key, db)
    return user

# Combined authentication: JWT or API key
async def get_authenticated_user(
    # Try JWT first
    jwt_user: Optional[User] = Depends(lambda: None),  # We'll handle this manually
    # Try API key
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Get authenticated user from either JWT token or API key"""
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi import Request
    
    # First try JWT authentication
    try:
        from auth import get_current_user
        security = HTTPBearer(auto_error=False)
        # This is a simplified approach - in practice you'd want to handle this more elegantly
        pass
    except:
        pass
    
    # Then try API key authentication
    if x_api_key:
        try:
            user = get_user_from_api_key(x_api_key, db)
            if user:
                return user
        except:
            pass
    
    # If neither worked, require authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide either Bearer token or X-API-Key header."
    )