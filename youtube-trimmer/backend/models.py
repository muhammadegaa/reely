"""
Database models for Reely - YouTube trimmer SaaS
"""
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()

class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(String(20), default=SubscriptionTier.FREE.value)
    stripe_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Usage tracking
    monthly_trim_count = Column(Integer, default=0)
    monthly_hook_count = Column(Integer, default=0)
    last_usage_reset = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional profile fields
    avatar_url = Column(String(500), nullable=True)
    timezone = Column(String(50), default="UTC")
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    video_jobs = relationship("VideoJob", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")
    usage_stats = relationship("UsageStats", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    tier = Column(String(20), nullable=False)
    status = Column(String(50), nullable=False)  # active, canceled, past_due, etc.
    current_period_start = Column(DateTime(timezone=True))
    current_period_end = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="subscriptions")

class VideoJob(Base):
    __tablename__ = "video_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(String(255), unique=True, index=True, nullable=False)  # UUID
    
    # Input parameters
    youtube_url = Column(Text, nullable=False)
    start_time = Column(Float, nullable=True)  # seconds
    end_time = Column(Float, nullable=True)  # seconds
    vertical_format = Column(Boolean, default=False)
    add_subtitles = Column(Boolean, default=False)
    ai_provider = Column(String(50), nullable=True)  # for hook detection
    
    # Processing info
    status = Column(String(20), default=ProcessingStatus.PENDING.value)
    error_message = Column(Text, nullable=True)
    original_duration = Column(Float, nullable=True)
    trimmed_duration = Column(Float, nullable=True)
    
    # File paths (stored in cloud storage)
    output_file_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    
    # AI-generated data
    hooks_data = Column(JSON, nullable=True)  # Array of hook objects
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="video_jobs")

class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action_type = Column(String(50), nullable=False)  # trim, hook_detection
    job_id = Column(String(255), nullable=True)  # Reference to video job
    credits_used = Column(Integer, default=1)
    usage_metadata = Column(JSON, nullable=True)  # Additional tracking data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="usage_logs")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    key_preview = Column(String(20), nullable=False)  # Last 4 chars for display
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_request_ip = Column(String(45), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")

class UsageStats(Base):
    __tablename__ = "usage_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String(7), nullable=False)  # Format: YYYY-MM
    year = Column(Integer, nullable=False)
    month_num = Column(Integer, nullable=False)
    
    # Usage counts
    trims_count = Column(Integer, default=0)
    hooks_count = Column(Integer, default=0)
    api_requests_count = Column(Integer, default=0)
    
    # Usage limits (can override subscription defaults)
    trims_limit = Column(Integer, nullable=True)
    hooks_limit = Column(Integer, nullable=True)
    
    # Video processing stats
    total_processing_time = Column(Float, default=0.0)  # seconds
    total_video_duration = Column(Float, default=0.0)  # seconds
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="usage_stats")
    
    # Unique constraint
    __table_args__ = (
        {"sqlite_autoincrement": True},
    )

# Utility functions for usage tracking
def get_current_usage_month():
    """Get current month in YYYY-MM format"""
    return datetime.now(timezone.utc).strftime("%Y-%m")

def get_or_create_usage_stats(db_session, user_id: int, month: str = None):
    """Get or create usage stats for a user and month"""
    if month is None:
        month = get_current_usage_month()
    
    year, month_num = month.split("-")
    year, month_num = int(year), int(month_num)
    
    usage_stats = db_session.query(UsageStats).filter(
        UsageStats.user_id == user_id,
        UsageStats.year == year,
        UsageStats.month_num == month_num
    ).first()
    
    if not usage_stats:
        usage_stats = UsageStats(
            user_id=user_id,
            month=month,
            year=year,
            month_num=month_num
        )
        db_session.add(usage_stats)
        db_session.commit()
    
    return usage_stats

# Subscription tier limits configuration
SUBSCRIPTION_LIMITS = {
    SubscriptionTier.FREE: {
        "monthly_trims": 5,
        "monthly_hooks": 3,
        "max_video_duration": 300,  # 5 minutes
        "max_file_size_mb": 50,
        "api_access": False,
        "priority_processing": False,
        "concurrent_jobs": 1,
        "features": ["basic_trim", "download"]
    },
    SubscriptionTier.PRO: {
        "monthly_trims": 100,
        "monthly_hooks": 50,
        "max_video_duration": 1800,  # 30 minutes
        "max_file_size_mb": 200,
        "api_access": True,
        "priority_processing": False,
        "concurrent_jobs": 3,
        "features": ["basic_trim", "vertical_format", "subtitles", "hook_detection", "download", "api_access", "bulk_upload"]
    },
    SubscriptionTier.PREMIUM: {
        "monthly_trims": -1,  # Unlimited
        "monthly_hooks": -1,  # Unlimited
        "max_video_duration": 7200,  # 2 hours
        "max_file_size_mb": 500,
        "api_access": True,
        "priority_processing": True,
        "concurrent_jobs": 10,
        "features": ["basic_trim", "vertical_format", "subtitles", "hook_detection", "download", "api_access", "priority_processing", "bulk_processing", "custom_branding", "webhook_notifications"]
    }
}

def check_usage_limits(user: User, action_type: str, db_session) -> dict:
    """Check if user has exceeded usage limits"""
    limits = SUBSCRIPTION_LIMITS.get(user.subscription_tier, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE])
    current_month = get_current_usage_month()
    usage_stats = get_or_create_usage_stats(db_session, user.id, current_month)
    
    result = {
        "allowed": True,
        "reason": None,
        "usage_stats": {
            "trims_used": usage_stats.trims_count,
            "hooks_used": usage_stats.hooks_count,
            "trims_limit": limits["monthly_trims"],
            "hooks_limit": limits["monthly_hooks"]
        }
    }
    
    if action_type == "trim":
        if limits["monthly_trims"] != -1 and usage_stats.trims_count >= limits["monthly_trims"]:
            result["allowed"] = False
            result["reason"] = f"Monthly trim limit of {limits['monthly_trims']} exceeded"
    
    elif action_type == "hook_detection":
        if limits["monthly_hooks"] != -1 and usage_stats.hooks_count >= limits["monthly_hooks"]:
            result["allowed"] = False
            result["reason"] = f"Monthly AI hooks limit of {limits['monthly_hooks']} exceeded"
    
    return result

def increment_usage(user: User, action_type: str, db_session, metadata: dict = None):
    """Increment usage count for a user action"""
    current_month = get_current_usage_month()
    usage_stats = get_or_create_usage_stats(db_session, user.id, current_month)
    
    if action_type == "trim":
        usage_stats.trims_count += 1
        user.monthly_trim_count += 1
    elif action_type == "hook_detection":
        usage_stats.hooks_count += 1
        user.monthly_hook_count += 1
    elif action_type == "api_request":
        usage_stats.api_requests_count += 1
    
    # Add processing time and video duration if provided
    if metadata:
        if "processing_time" in metadata:
            usage_stats.total_processing_time += metadata["processing_time"]
        if "video_duration" in metadata:
            usage_stats.total_video_duration += metadata["video_duration"]
    
    # Create usage log entry
    usage_log = UsageLog(
        user_id=user.id,
        action_type=action_type,
        job_id=metadata.get("job_id") if metadata else None,
        usage_metadata=metadata
    )
    db_session.add(usage_log)
    db_session.commit()