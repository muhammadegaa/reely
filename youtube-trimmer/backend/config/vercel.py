"""
Vercel-specific configuration for Reely
Optimizations and settings for serverless deployment
"""
import os
from typing import Dict, Any, List
from config import Settings

class VercelSettings(Settings):
    """Vercel-specific settings that override base settings"""
    
    # Serverless optimizations
    max_request_timeout: int = 300  # 5 minutes (Vercel limit)
    enable_background_cleanup: bool = False  # Disable in serverless
    use_sqlite: bool = False  # Force PostgreSQL in production
    
    # File handling for serverless
    temp_file_cleanup_hours: int = 1  # Faster cleanup
    max_file_size_mb: int = 50  # Smaller files for serverless
    
    # Connection pooling adjustments for serverless
    db_pool_size: int = 5  # Smaller pool for serverless
    db_max_overflow: int = 10
    db_pool_timeout: int = 20
    db_pool_recycle: int = 1800  # 30 minutes
    
    # Redis optimizations
    redis_pool_max_connections: int = 10
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    @property
    def is_vercel(self) -> bool:
        """Check if running on Vercel"""
        return os.getenv("VERCEL") == "1"
    
    @property
    def vercel_url(self) -> str:
        """Get Vercel deployment URL"""
        return os.getenv("VERCEL_URL", "localhost")
    
    @property
    def vercel_region(self) -> str:
        """Get Vercel region"""
        return os.getenv("VERCEL_REGION", "unknown")
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins with Vercel URL included"""
        origins = self.cors_origins.copy()
        
        if self.is_vercel:
            # Add Vercel URL to CORS origins
            vercel_url = f"https://{self.vercel_url}"
            if vercel_url not in origins:
                origins.append(vercel_url)
        
        return origins
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration optimized for Vercel"""
        config = {
            "pool_size": self.db_pool_size,
            "max_overflow": self.db_max_overflow,
            "pool_timeout": self.db_pool_timeout,
            "pool_recycle": self.db_pool_recycle,
            "pool_pre_ping": True,
        }
        
        if self.is_vercel:
            # Additional Vercel-specific optimizations
            config.update({
                "connect_args": {
                    "sslmode": "require",  # Force SSL
                    "options": "-c timezone=UTC",
                    "application_name": f"reely_vercel_{self.vercel_region}",
                    "connect_timeout": 10,
                }
            })
        
        return config
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration optimized for Vercel"""
        config = {
            "socket_timeout": self.redis_socket_timeout,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "max_connections": self.redis_pool_max_connections,
        }
        
        if self.is_vercel:
            # Vercel-specific Redis optimizations
            config.update({
                "ssl_cert_reqs": None,  # For Upstash Redis
                "decode_responses": True,
            })
        
        return config
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get feature flags for Vercel deployment"""
        flags = super().get_feature_flags()
        
        if self.is_vercel:
            # Disable features that don't work well in serverless
            flags.update({
                "background_cleanup": False,
                "long_running_tasks": False,
                "file_system_cache": False,
                "local_file_storage": False,
            })
        
        return flags

def get_vercel_settings() -> VercelSettings:
    """Get Vercel-optimized settings"""
    return VercelSettings()

# Middleware for Vercel-specific headers
def add_vercel_headers():
    """Add Vercel-specific response headers"""
    def middleware(request, call_next):
        import time
        from starlette.responses import Response
        
        start_time = time.time()
        response: Response = call_next(request)
        process_time = time.time() - start_time
        
        # Add Vercel-specific headers
        if os.getenv("VERCEL") == "1":
            response.headers["x-vercel-region"] = os.getenv("VERCEL_REGION", "unknown")
            response.headers["x-vercel-deployment"] = os.getenv("VERCEL_DEPLOYMENT_ID", "unknown")
            response.headers["x-process-time"] = str(process_time)
            response.headers["x-powered-by"] = "Reely on Vercel"
        
        return response
    
    return middleware

# Database connection optimization for serverless
def create_serverless_engine(database_url: str):
    """Create SQLAlchemy engine optimized for serverless"""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool
    
    settings = get_vercel_settings()
    
    # Use NullPool for serverless to avoid connection pooling issues
    engine = create_engine(
        database_url,
        poolclass=NullPool,  # No connection pooling in serverless
        echo=settings.debug,
        **settings.get_database_config()
    )
    
    return engine

# Redis client optimization for serverless  
def create_serverless_redis(redis_url: str):
    """Create Redis client optimized for serverless"""
    import redis
    from urllib.parse import urlparse
    
    settings = get_vercel_settings()
    config = settings.get_redis_config()
    
    # Parse Redis URL
    parsed = urlparse(redis_url)
    
    # Create Redis client with optimizations
    client = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        ssl=parsed.scheme == "rediss",
        **config
    )
    
    return client

# Health check optimized for Vercel
def vercel_health_check() -> Dict[str, Any]:
    """Health check specifically for Vercel deployment"""
    import time
    
    start_time = time.time()
    
    health_data = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": "vercel" if os.getenv("VERCEL") == "1" else "local",
        "region": os.getenv("VERCEL_REGION", "unknown"),
        "deployment_id": os.getenv("VERCEL_DEPLOYMENT_ID", "unknown"),
        "version": "2.0.0",
        "features": get_vercel_settings().get_feature_flags()
    }
    
    # Test database connection
    try:
        from database import test_database_connection
        health_data["database"] = "connected" if test_database_connection() else "disconnected"
    except Exception as e:
        health_data["database"] = f"error: {str(e)}"
    
    # Test Redis connection
    try:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            client = create_serverless_redis(redis_url)
            client.ping()
            health_data["redis"] = "connected"
        else:
            health_data["redis"] = "not_configured"
    except Exception as e:
        health_data["redis"] = f"error: {str(e)}"
    
    health_data["response_time"] = time.time() - start_time
    
    return health_data