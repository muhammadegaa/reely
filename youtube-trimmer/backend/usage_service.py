"""
Usage tracking and enforcement service for Reely
Handles subscription limits, usage counting, and analytics
"""
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import (
    User, UsageStats, UsageLog, VideoJob, APIKey,
    SubscriptionTier, SUBSCRIPTION_LIMITS,
    get_current_usage_month, get_or_create_usage_stats,
    check_usage_limits, increment_usage
)
from database import get_db_session
import logging

logger = logging.getLogger(__name__)

class UsageService:
    """Service for managing user usage tracking and enforcement"""
    
    @staticmethod
    def check_user_limits(user: User, action_type: str, db_session: Session, **kwargs) -> Dict[str, Any]:
        """
        Check if user can perform an action based on their subscription limits
        
        Args:
            user: User instance
            action_type: Type of action (trim, hook_detection, api_request)
            db_session: Database session
            **kwargs: Additional parameters (video_duration, etc.)
        
        Returns:
            Dict with 'allowed' boolean and additional info
        """
        try:
            # Get user's subscription limits
            limits = SUBSCRIPTION_LIMITS.get(user.subscription_tier, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE])
            
            # Check basic usage limits
            usage_check = check_usage_limits(user, action_type, db_session)
            if not usage_check["allowed"]:
                return usage_check
            
            # Additional checks based on action type
            result = {
                "allowed": True,
                "reason": None,
                "limits": limits,
                "usage_stats": usage_check["usage_stats"]
            }
            
            # Video duration check for video processing
            if action_type in ["trim", "hook_detection"] and "video_duration" in kwargs:
                video_duration = kwargs["video_duration"]
                max_duration = limits["max_video_duration"]
                
                if video_duration > max_duration:
                    result["allowed"] = False
                    result["reason"] = f"Video duration ({video_duration}s) exceeds limit ({max_duration}s) for {user.subscription_tier} tier"
                    return result
            
            # File size check
            if "file_size_mb" in kwargs:
                file_size = kwargs["file_size_mb"]
                max_size = limits.get("max_file_size_mb", 100)
                
                if file_size > max_size:
                    result["allowed"] = False
                    result["reason"] = f"File size ({file_size}MB) exceeds limit ({max_size}MB) for {user.subscription_tier} tier"
                    return result
            
            # Feature access check
            if "required_feature" in kwargs:
                feature = kwargs["required_feature"]
                if feature not in limits["features"]:
                    result["allowed"] = False
                    result["reason"] = f"Feature '{feature}' not available in {user.subscription_tier} tier"
                    return result
            
            # Concurrent jobs check
            if action_type == "trim":
                active_jobs = db_session.query(VideoJob).filter(
                    VideoJob.user_id == user.id,
                    VideoJob.status.in_(["pending", "processing"])
                ).count()
                
                max_concurrent = limits.get("concurrent_jobs", 1)
                if active_jobs >= max_concurrent:
                    result["allowed"] = False
                    result["reason"] = f"Maximum concurrent jobs ({max_concurrent}) reached"
                    return result
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking user limits: {e}")
            return {
                "allowed": False,
                "reason": "Error checking limits",
                "error": str(e)
            }
    
    @staticmethod
    def record_usage(user: User, action_type: str, db_session: Session, **metadata) -> bool:
        """
        Record usage of a feature by a user
        
        Args:
            user: User instance
            action_type: Type of action performed
            db_session: Database session
            **metadata: Additional metadata to store
        
        Returns:
            Boolean indicating success
        """
        try:
            increment_usage(user, action_type, db_session, metadata)
            return True
            
        except Exception as e:
            logger.error(f"Error recording usage: {e}")
            return False
    
    @staticmethod
    def get_user_usage_summary(user: User, db_session: Session, months: int = 1) -> Dict[str, Any]:
        """
        Get comprehensive usage summary for a user
        
        Args:
            user: User instance
            db_session: Database session
            months: Number of months to include in summary
        
        Returns:
            Dictionary with usage statistics
        """
        try:
            # Get current month stats
            current_month = get_current_usage_month()
            current_stats = get_or_create_usage_stats(db_session, user.id, current_month)
            
            # Get limits
            limits = SUBSCRIPTION_LIMITS.get(user.subscription_tier, SUBSCRIPTION_LIMITS[SubscriptionTier.FREE])
            
            # Calculate usage over the specified period
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30 * months)
            
            # Get historical usage
            historical_usage = db_session.query(UsageLog).filter(
                UsageLog.user_id == user.id,
                UsageLog.created_at >= start_date
            ).all()
            
            # Aggregate historical data
            usage_by_type = {}
            for log in historical_usage:
                action_type = log.action_type
                if action_type not in usage_by_type:
                    usage_by_type[action_type] = []
                usage_by_type[action_type].append({
                    "date": log.created_at,
                    "metadata": log.usage_metadata
                })
            
            # Get video job statistics
            job_stats = db_session.query(VideoJob.status, func.count(VideoJob.id)).filter(
                VideoJob.user_id == user.id,
                VideoJob.created_at >= start_date
            ).group_by(VideoJob.status).all()
            
            job_stats_dict = {status: count for status, count in job_stats}
            
            return {
                "user_id": user.id,
                "subscription_tier": user.subscription_tier,
                "period": {
                    "start": start_date,
                    "end": end_date,
                    "months": months
                },
                "current_month": {
                    "month": current_month,
                    "trims_used": current_stats.trims_count,
                    "hooks_used": current_stats.hooks_count,
                    "api_requests": current_stats.api_requests_count,
                    "total_processing_time": current_stats.total_processing_time,
                    "total_video_duration": current_stats.total_video_duration
                },
                "limits": {
                    "monthly_trims": limits["monthly_trims"],
                    "monthly_hooks": limits["monthly_hooks"],
                    "max_video_duration": limits["max_video_duration"],
                    "max_file_size_mb": limits.get("max_file_size_mb", 100),
                    "concurrent_jobs": limits.get("concurrent_jobs", 1),
                    "features": limits["features"]
                },
                "usage_percentage": {
                    "trims": (current_stats.trims_count / limits["monthly_trims"] * 100) if limits["monthly_trims"] > 0 else 0,
                    "hooks": (current_stats.hooks_count / limits["monthly_hooks"] * 100) if limits["monthly_hooks"] > 0 else 0
                },
                "historical_usage": usage_by_type,
                "job_statistics": job_stats_dict
            }
            
        except Exception as e:
            logger.error(f"Error getting usage summary: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def reset_user_monthly_usage(user_id: int, db_session: Session) -> bool:
        """
        Reset monthly usage counters for a specific user
        
        Args:
            user_id: User ID to reset
            db_session: Database session
        
        Returns:
            Boolean indicating success
        """
        try:
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Reset counters
            user.monthly_trim_count = 0
            user.monthly_hook_count = 0
            user.last_usage_reset = datetime.now(timezone.utc)
            
            db_session.commit()
            
            logger.info(f"Reset monthly usage for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting monthly usage: {e}")
            return False
    
    @staticmethod
    def get_system_usage_analytics(db_session: Session, days: int = 30) -> Dict[str, Any]:
        """
        Get system-wide usage analytics
        
        Args:
            db_session: Database session
            days: Number of days to analyze
        
        Returns:
            Dictionary with system analytics
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # User statistics
            total_users = db_session.query(User).count()
            active_users = db_session.query(User).filter(
                User.last_login >= start_date
            ).count()
            
            # Subscription breakdown
            subscription_stats = db_session.query(
                User.subscription_tier,
                func.count(User.id)
            ).group_by(User.subscription_tier).all()
            
            # Usage statistics
            usage_stats = db_session.query(
                UsageLog.action_type,
                func.count(UsageLog.id)
            ).filter(
                UsageLog.created_at >= start_date
            ).group_by(UsageLog.action_type).all()
            
            # Job statistics
            job_stats = db_session.query(
                VideoJob.status,
                func.count(VideoJob.id)
            ).filter(
                VideoJob.created_at >= start_date
            ).group_by(VideoJob.status).all()
            
            # API key usage
            api_stats = db_session.query(
                func.count(APIKey.id),
                func.sum(APIKey.total_requests)
            ).filter(
                APIKey.is_active == True
            ).first()
            
            # Daily usage trend
            daily_usage = db_session.query(
                func.date(UsageLog.created_at).label('date'),
                func.count(UsageLog.id)
            ).filter(
                UsageLog.created_at >= start_date
            ).group_by(
                func.date(UsageLog.created_at)
            ).order_by('date').all()
            
            return {
                "period": {
                    "start": start_date,
                    "end": end_date,
                    "days": days
                },
                "users": {
                    "total": total_users,
                    "active": active_users,
                    "activity_rate": (active_users / total_users * 100) if total_users > 0 else 0
                },
                "subscriptions": {
                    tier: count for tier, count in subscription_stats
                },
                "usage": {
                    action_type: count for action_type, count in usage_stats
                },
                "jobs": {
                    status: count for status, count in job_stats
                },
                "api": {
                    "active_keys": api_stats[0] or 0,
                    "total_requests": api_stats[1] or 0
                },
                "daily_trend": [
                    {"date": str(date), "usage": count}
                    for date, count in daily_usage
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting system analytics: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def check_and_enforce_limits(user: User, action_type: str, db_session: Session, **kwargs):
        """
        Decorator/middleware function to check and enforce limits
        
        Usage:
            @check_and_enforce_limits(user, "trim", db_session, video_duration=600)
            def process_video(...):
                pass
        """
        def decorator(func):
            def wrapper(*args, **func_kwargs):
                # Check limits
                limit_check = UsageService.check_user_limits(
                    user, action_type, db_session, **kwargs
                )
                
                if not limit_check["allowed"]:
                    raise Exception(limit_check["reason"])
                
                # Execute the function
                result = func(*args, **func_kwargs)
                
                # Record usage on success
                UsageService.record_usage(
                    user, action_type, db_session,
                    job_id=func_kwargs.get("job_id"),
                    **kwargs
                )
                
                return result
            return wrapper
        return decorator

# Convenience functions for common usage patterns
def can_user_trim_video(user: User, video_duration: int, db_session: Session) -> Dict[str, Any]:
    """Check if user can trim a video of given duration"""
    return UsageService.check_user_limits(
        user, "trim", db_session, video_duration=video_duration
    )

def can_user_detect_hooks(user: User, db_session: Session) -> Dict[str, Any]:
    """Check if user can use AI hook detection"""
    return UsageService.check_user_limits(
        user, "hook_detection", db_session, required_feature="hook_detection"
    )

def record_video_trim(user: User, db_session: Session, job_id: str, video_duration: float, processing_time: float):
    """Record a video trim operation"""
    return UsageService.record_usage(
        user, "trim", db_session,
        job_id=job_id,
        video_duration=video_duration,
        processing_time=processing_time
    )

def record_hook_detection(user: User, db_session: Session, job_id: str, hooks_found: int):
    """Record an AI hook detection operation"""
    return UsageService.record_usage(
        user, "hook_detection", db_session,
        job_id=job_id,
        hooks_found=hooks_found
    )

def get_monthly_usage_report(user: User, db_session: Session) -> Dict[str, Any]:
    """Get a user's monthly usage report"""
    return UsageService.get_user_usage_summary(user, db_session, months=1)

# Background tasks for usage management
def cleanup_old_usage_logs(days_to_keep: int = 90):
    """Clean up old usage logs to manage database size"""
    try:
        with get_db_session() as db:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            old_logs = db.query(UsageLog).filter(
                UsageLog.created_at < cutoff_date
            )
            
            count = old_logs.count()
            old_logs.delete(synchronize_session=False)
            
            db.commit()
            logger.info(f"Cleaned up {count} old usage logs")
            
    except Exception as e:
        logger.error(f"Error cleaning up usage logs: {e}")

def generate_usage_reports():
    """Generate monthly usage reports for all users"""
    try:
        with get_db_session() as db:
            users = db.query(User).filter(User.is_active == True).all()
            
            reports = []
            for user in users:
                report = UsageService.get_user_usage_summary(user, db)
                reports.append(report)
            
            logger.info(f"Generated usage reports for {len(reports)} users")
            return reports
            
    except Exception as e:
        logger.error(f"Error generating usage reports: {e}")
        return []