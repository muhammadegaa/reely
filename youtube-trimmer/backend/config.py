"""
Configuration management for Reely
Handles different environments (development, staging, production)
"""
import os
from typing import List, Optional
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment-specific configurations"""
    
    # Application
    app_name: str = "Reely"
    app_version: str = "2.0.0"
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = environment == "development"
    
    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://reely_user:reely_password@localhost:5432/reely_db"
    )
    use_sqlite: bool = os.getenv("USE_SQLITE", "false").lower() == "true"
    
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Security
    jwt_secret_key: str = os.getenv(
        "JWT_SECRET_KEY", 
        "your-super-secret-jwt-key-change-this-in-production"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: List[str] = [
        origin.strip() 
        for origin in os.getenv(
            "CORS_ORIGINS", 
            "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
    ]
    
    # API Keys
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    
    # Stripe
    stripe_secret_key: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
    stripe_publishable_key: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
    stripe_webhook_secret: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")
    stripe_price_id_pro: Optional[str] = os.getenv("STRIPE_PRICE_ID_PRO")
    stripe_price_id_premium: Optional[str] = os.getenv("STRIPE_PRICE_ID_PREMIUM")
    
    # AWS
    aws_access_key_id: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: Optional[str] = os.getenv("S3_BUCKET_NAME")
    
    # Email
    smtp_host: Optional[str] = os.getenv("SMTP_HOST")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: Optional[str] = os.getenv("SMTP_USER")
    smtp_password: Optional[str] = os.getenv("SMTP_PASSWORD")
    
    # Rate Limiting
    rate_limit_requests_per_minute: int = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
    rate_limit_burst: int = int(os.getenv("RATE_LIMIT_BURST", "10"))
    
    # Authentication Rate Limiting
    max_login_attempts: int = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    lockout_duration_minutes: int = int(os.getenv("LOCKOUT_DURATION_MINUTES", "15"))
    
    # API Key Settings
    api_key_expire_days: int = int(os.getenv("API_KEY_EXPIRE_DAYS", "365"))
    max_api_keys_per_user: int = int(os.getenv("MAX_API_KEYS_PER_USER", "5"))
    
    # Monitoring
    sentry_dsn: Optional[str] = os.getenv("SENTRY_DSN")
    
    # File Storage
    max_file_size_mb: int = 100
    temp_file_cleanup_hours: int = 24
    
    # Video Processing
    max_video_duration_seconds: int = 7200  # 2 hours
    default_video_quality: str = "720p"
    supported_formats: List[str] = ["mp4", "webm", "avi", "mov"]
    
    # Processing Timeouts (in seconds)
    sync_processing_timeout: int = 300  # 5 minutes for sync processing
    async_processing_timeout: int = 3600  # 1 hour for async processing
    download_timeout: int = 600  # 10 minutes for video downloads
    transcription_timeout: int = 1800  # 30 minutes for transcription
    ffmpeg_timeout: int = 1800  # 30 minutes for video processing
    
    # Processing Quality Settings
    enable_fast_processing: bool = os.getenv("ENABLE_FAST_PROCESSING", "true").lower() == "true"
    max_concurrent_jobs: int = int(os.getenv("MAX_CONCURRENT_JOBS", "3"))
    use_gpu_acceleration: bool = os.getenv("USE_GPU_ACCELERATION", "false").lower() == "true"
    
    # Async Processing (Celery/Redis)
    enable_async_processing: bool = os.getenv("ENABLE_ASYNC_PROCESSING", "true").lower() == "true"
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", settings.redis_url if 'settings' in locals() else "redis://localhost:6379/0")
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", settings.redis_url if 'settings' in locals() else "redis://localhost:6379/0")
    
    # Auto-optimization thresholds
    auto_async_duration_threshold: int = 300  # Auto-use async for videos longer than 5 minutes
    auto_async_with_subtitles: bool = True  # Always use async when subtitles are requested
    auto_async_vertical_format: bool = True  # Always use async for vertical format processing
    
    # Subscription Limits (can be overridden by database)
    free_tier_monthly_trims: int = 5
    free_tier_monthly_hooks: int = 3
    pro_tier_monthly_trims: int = 100
    pro_tier_monthly_hooks: int = 50
    
    # Usage Analytics
    analytics_retention_days: int = int(os.getenv("ANALYTICS_RETENTION_DAYS", "90"))
    enable_usage_analytics: bool = os.getenv("ENABLE_USAGE_ANALYTICS", "true").lower() == "true"
    
    # Background Jobs
    enable_background_cleanup: bool = os.getenv("ENABLE_BACKGROUND_CLEANUP", "true").lower() == "true"
    cleanup_interval_hours: int = int(os.getenv("CLEANUP_INTERVAL_HOURS", "24"))
    
    # Security Headers
    enable_security_headers: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for SQLAlchemy"""
        if self.use_sqlite:
            return "sqlite:///./reely_dev.db"
        return self.database_url.replace("postgresql://", "postgresql+psycopg2://")
    
    def get_database_url(self, async_driver: bool = False) -> str:
        """Get database URL with appropriate driver"""
        if self.use_sqlite:
            return "sqlite:///./reely_dev.db"
        
        if async_driver:
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
        else:
            return self.database_url.replace("postgresql://", "postgresql+psycopg2://")

# Create settings instance
settings = Settings()

# Environment-specific configurations
class DevelopmentConfig(Settings):
    """Development environment configuration"""
    debug: bool = True
    reload: bool = True
    use_sqlite: bool = True

class ProductionConfig(Settings):
    """Production environment configuration"""
    debug: bool = False
    reload: bool = False
    use_sqlite: bool = False
    
    # Override with more restrictive settings
    rate_limit_requests_per_minute: int = 30
    rate_limit_burst: int = 5
    max_file_size_mb: int = 50

class TestingConfig(Settings):
    """Testing environment configuration"""
    debug: bool = True
    use_sqlite: bool = True
    database_url: str = "sqlite:///./test.db"

def get_settings() -> Settings:
    """Get settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionConfig()
    elif env == "testing":
        return TestingConfig()
    else:
        return DevelopmentConfig()

# Validation functions
def validate_required_settings():
    """Validate that required settings are present"""
    errors = []
    
    if settings.is_production:
        # Production-specific validations
        if not settings.jwt_secret_key or settings.jwt_secret_key == "your-super-secret-jwt-key-change-this-in-production":
            errors.append("JWT_SECRET_KEY must be set to a secure value in production")
        
        if not settings.openai_api_key and not settings.anthropic_api_key:
            errors.append("At least one AI API key (OPENAI_API_KEY or ANTHROPIC_API_KEY) must be set")
        
        if not settings.stripe_secret_key:
            errors.append("STRIPE_SECRET_KEY must be set in production")
        
        if not settings.database_url or "localhost" in settings.database_url:
            errors.append("DATABASE_URL must be set to a production database")
    
    if errors:
        raise ValueError("Configuration errors:\n" + "\n".join(f"- {error}" for error in errors))

def get_feature_flags() -> dict:
    """Get feature flags based on environment and subscription"""
    return {
        "ai_hook_detection": bool(settings.openai_api_key or settings.anthropic_api_key),
        "stripe_payments": bool(settings.stripe_secret_key),
        "email_notifications": bool(settings.smtp_host and settings.smtp_user),
        "cloud_storage": bool(settings.s3_bucket_name),
        "error_tracking": bool(settings.sentry_dsn),
        "rate_limiting": True,  # Always enabled
        "user_analytics": settings.enable_usage_analytics,
        "api_access": True,
        "webhook_support": settings.is_production,
        "background_cleanup": settings.enable_background_cleanup,
        "security_headers": settings.enable_security_headers,
        "redis_caching": bool(settings.redis_url),
        "async_processing": settings.enable_async_processing,
        "fast_processing": settings.enable_fast_processing,
        "gpu_acceleration": settings.use_gpu_acceleration
    }

def get_processing_config() -> dict:
    """Get video processing configuration"""
    return {
        "timeouts": {
            "sync_processing": settings.sync_processing_timeout,
            "async_processing": settings.async_processing_timeout,
            "download": settings.download_timeout,
            "transcription": settings.transcription_timeout,
            "ffmpeg": settings.ffmpeg_timeout
        },
        "quality": {
            "enable_fast_processing": settings.enable_fast_processing,
            "use_gpu_acceleration": settings.use_gpu_acceleration,
            "max_concurrent_jobs": settings.max_concurrent_jobs
        },
        "async_thresholds": {
            "duration_threshold": settings.auto_async_duration_threshold,
            "auto_async_with_subtitles": settings.auto_async_with_subtitles,
            "auto_async_vertical_format": settings.auto_async_vertical_format
        }
    }

def get_subscription_config() -> dict:
    """Get subscription configuration"""
    return {
        "tiers": {
            "free": {
                "name": "Free",
                "price": 0,
                "monthly_trims": settings.free_tier_monthly_trims,
                "monthly_hooks": settings.free_tier_monthly_hooks,
                "max_video_duration": 300,  # 5 minutes
                "features": ["basic_trim", "download"]
            },
            "pro": {
                "name": "Pro",
                "price": 9.99,
                "monthly_trims": settings.pro_tier_monthly_trims,
                "monthly_hooks": settings.pro_tier_monthly_hooks,
                "max_video_duration": 1800,  # 30 minutes
                "features": ["basic_trim", "vertical_format", "subtitles", "hook_detection", "download", "api_access"]
            },
            "premium": {
                "name": "Premium",
                "price": 29.99,
                "monthly_trims": -1,  # Unlimited
                "monthly_hooks": -1,  # Unlimited
                "max_video_duration": 7200,  # 2 hours
                "features": ["basic_trim", "vertical_format", "subtitles", "hook_detection", "download", "api_access", "priority_processing", "webhook_notifications", "async_processing", "fast_processing"]
            }
        }
    }

def get_rate_limit_config() -> dict:
    """Get rate limiting configuration"""
    return {
        "api": {
            "requests_per_minute": settings.rate_limit_requests_per_minute,
            "burst": settings.rate_limit_burst
        },
        "auth": {
            "max_login_attempts": settings.max_login_attempts,
            "lockout_duration_minutes": settings.lockout_duration_minutes
        },
        "api_keys": {
            "max_per_user": settings.max_api_keys_per_user,
            "expire_days": settings.api_key_expire_days
        }
    }

# Initialize settings
settings = get_settings()

# Validate settings on import
if __name__ == "__main__":
    try:
        validate_required_settings()
        print("✅ Configuration validation passed")
        print(f"Environment: {settings.environment}")
        print(f"Debug: {settings.debug}")
        print(f"Database: {'SQLite' if settings.use_sqlite else 'PostgreSQL'}")
        print("Feature flags:", get_feature_flags())
        print("\nSubscription configuration:")
        for tier, config in get_subscription_config()["tiers"].items():
            print(f"  {tier}: {config['monthly_trims']} trims, {config['monthly_hooks']} hooks")
        print("\nRate limiting:", get_rate_limit_config())
    except ValueError as e:
        print(f"❌ Configuration validation failed:\n{e}")
        exit(1)