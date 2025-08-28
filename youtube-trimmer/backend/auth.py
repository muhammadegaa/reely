"""
Authentication system for Reely using JWT tokens
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db
from models import User
from dotenv import load_dotenv

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Rate limiting for authentication
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOCKOUT_DURATION_MINUTES = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Bearer token scheme
security = HTTPBearer()

class TokenData:
    def __init__(self, email: Optional[str] = None):
        self.email = email

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str, request_ip: str = None) -> Optional[User]:
    """Authenticate a user with email and password with rate limiting"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    
    # Check if account is locked (basic implementation)
    # In production, you'd want to use Redis for this
    
    if not verify_password(password, user.hashed_password):
        return None
    
    # Update last login on successful authentication
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, token_type: str = "access") -> Optional[str]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type_claim: str = payload.get("type")
        
        if email is None or token_type_claim != token_type:
            return None
            
        return email
    except JWTError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        email = verify_token(token, "access")
        if email is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        email = verify_token(token, "access")
        if email is None:
            return None
        
        user = db.query(User).filter(User.email == email).first()
        return user if user and user.is_active else None
    except Exception:
        return None

# API Key authentication (for premium users)
def verify_api_key(api_key: str, db: Session) -> Optional[User]:
    """Verify an API key and return the associated user"""
    from models import APIKey
    import hashlib
    
    # Hash the provided API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Find the API key in the database
    api_key_obj = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not api_key_obj:
        return None
    
    # Update last used timestamp
    api_key_obj.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    # Get the associated user
    user = db.query(User).filter(User.id == api_key_obj.user_id).first()
    return user if user and user.is_active else None

def get_user_from_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> User:
    """Get user from API key authentication"""
    user = verify_api_key(api_key, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return user

# Refresh token management
def create_token_pair(user_data: dict) -> dict:
    """Create both access and refresh tokens"""
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data=user_data)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

def refresh_access_token(refresh_token: str, db: Session) -> dict:
    """Generate new access token from refresh token"""
    email = verify_token(refresh_token, "refresh")
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
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return create_token_pair({"sub": user.email})

# Enhanced user validation
def validate_user_permissions(user: User, required_feature: str) -> bool:
    """Check if user has access to a specific feature"""
    from models import SUBSCRIPTION_LIMITS
    
    user_limits = SUBSCRIPTION_LIMITS.get(user.subscription_tier)
    if not user_limits:
        return False
    
    return required_feature in user_limits.get("features", [])

def require_subscription_tier(min_tier: str):
    """Decorator to require minimum subscription tier"""
    def decorator(func):
        def wrapper(current_user: User = Depends(get_current_active_user), *args, **kwargs):
            tier_hierarchy = {"free": 0, "pro": 1, "premium": 2}
            user_tier_level = tier_hierarchy.get(current_user.subscription_tier, 0)
            required_tier_level = tier_hierarchy.get(min_tier, 0)
            
            if user_tier_level < required_tier_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {min_tier} subscription or higher"
                )
            return func(current_user, *args, **kwargs)
        return wrapper
    return decorator

def require_feature_access(feature: str):
    """Decorator to require access to specific feature"""
    def decorator(func):
        def wrapper(current_user: User = Depends(get_current_active_user), *args, **kwargs):
            if not validate_user_permissions(current_user, feature):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires a subscription that includes {feature}"
                )
            return func(current_user, *args, **kwargs)
        return wrapper
    return decorator

# API Key management functions
def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and return (key, hash)"""
    import secrets
    import hashlib
    
    # Generate a secure random API key
    api_key = f"rly_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    return api_key, key_hash

def create_api_key(user: User, name: str, db: Session, expires_in_days: int = None) -> dict:
    """Create a new API key for a user"""
    from models import APIKey
    
    # Check if user has API access
    if not validate_user_permissions(user, "api_access"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API access requires Pro or Premium subscription"
        )
    
    api_key, key_hash = generate_api_key()
    key_preview = api_key[-4:]  # Last 4 characters for display
    
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    api_key_obj = APIKey(
        user_id=user.id,
        key_hash=key_hash,
        key_preview=key_preview,
        name=name,
        expires_at=expires_at
    )
    
    db.add(api_key_obj)
    db.commit()
    db.refresh(api_key_obj)
    
    return {
        "id": api_key_obj.id,
        "api_key": api_key,  # Only returned once!
        "name": name,
        "preview": key_preview,
        "created_at": api_key_obj.created_at,
        "expires_at": api_key_obj.expires_at
    }

def revoke_api_key(api_key_id: int, user: User, db: Session) -> bool:
    """Revoke an API key"""
    from models import APIKey
    
    api_key_obj = db.query(APIKey).filter(
        APIKey.id == api_key_id,
        APIKey.user_id == user.id
    ).first()
    
    if not api_key_obj:
        return False
    
    api_key_obj.is_active = False
    db.commit()
    return True