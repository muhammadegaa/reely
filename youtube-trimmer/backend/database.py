"""
Database configuration and session management for Reely
Enhanced with connection pooling and production optimizations
"""
import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DisconnectionError
from models import Base, User
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration with enhanced connection pooling
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://reely_user:reely_password@localhost:5432/reely_db"
)

# For development, you can use SQLite as fallback
SQLITE_URL = "sqlite:///./reely_dev.db"

# Determine which database to use
USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Connection pool settings
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))  # 1 hour
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

def setup_engine_events(engine: Engine):
    """Set up SQLAlchemy engine event listeners for monitoring and optimization"""
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragma for better performance"""
        if "sqlite" in str(engine.url):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()
    
    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection, branch):
        """Ensure connection is alive"""
        if branch:
            # "branch" refers to a sub-connection of a connection,
            # we don't want to bother pinging on these
            return
        
        # Run a SELECT 1 to check connectivity
        try:
            from sqlalchemy import text
            connection.scalar(text("SELECT 1"))
        except Exception as err:
            if isinstance(err, DisconnectionError):
                logger.warning("Database connection lost, reconnecting...")
                connection.invalidate()
                raise

def create_database_engine():
    """Create database engine with appropriate configuration"""
    if USE_SQLITE:
        logger.info("Using SQLite for development")
        engine = create_engine(
            SQLITE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=ENVIRONMENT == "development" and os.getenv("SQL_ECHO", "false").lower() == "true"
        )
    else:
        # Hide password in logs
        safe_url = DATABASE_URL
        if "@" in DATABASE_URL and "://" in DATABASE_URL:
            parts = DATABASE_URL.split("://")
            if len(parts) == 2:
                scheme = parts[0]
                rest = parts[1]
                if "@" in rest:
                    user_pass, host_db = rest.split("@", 1)
                    safe_url = f"{scheme}://***@{host_db}"
        
        logger.info(f"Using PostgreSQL: {safe_url}")
        
        engine = create_engine(
            DATABASE_URL,
            poolclass=QueuePool,
            pool_size=POOL_SIZE,
            max_overflow=MAX_OVERFLOW,
            pool_timeout=POOL_TIMEOUT,
            pool_recycle=POOL_RECYCLE,
            pool_pre_ping=POOL_PRE_PING,
            echo=ENVIRONMENT == "development" and os.getenv("SQL_ECHO", "false").lower() == "true",
            # Performance optimizations
            connect_args={
                "options": "-c timezone=UTC",
                "application_name": "reely_backend",
            } if not USE_SQLITE else {}
        )
    
    # Add connection event listeners
    setup_engine_events(engine)
    return engine

# Create engine
engine = create_database_engine()

# Session configuration
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Prevent lazy loading issues after commit
)

def create_tables():
    """Create all database tables"""
    try:
        # Use a fresh connection for table creation
        with engine.connect() as conn:
            Base.metadata.create_all(bind=conn)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise

def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def test_database_connection() -> bool:
    """Test database connectivity"""
    try:
        from sqlalchemy import text
        with get_db_session() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def get_database_stats() -> dict:
    """Get database connection pool statistics"""
    pool = engine.pool
    stats = {}
    
    # Different pool types have different methods available
    try:
        if hasattr(pool, 'size'):
            stats["pool_size"] = pool.size()
        if hasattr(pool, 'checkedin'):
            stats["checked_in"] = pool.checkedin()
        if hasattr(pool, 'checkedout'):
            stats["checked_out"] = pool.checkedout()
        if hasattr(pool, 'overflow'):
            stats["overflow"] = pool.overflow()
        if hasattr(pool, 'invalid'):
            stats["invalid"] = pool.invalid()
        
        # Add pool type info
        stats["pool_type"] = type(pool).__name__
    except Exception as e:
        stats["error"] = str(e)
        stats["pool_type"] = type(pool).__name__
    
    return stats

# Initialize database on import
def init_db():
    """Initialize the database with tables"""
    try:
        # Test connection first (skip for now to avoid SQLAlchemy text() issues)
        # if not test_database_connection():
        #     logger.warning("Database connection test failed during initialization")
        
        # Create tables
        create_tables()
        logger.info("Database initialization completed successfully")
        
        # Log connection info
        stats = get_database_stats()
        logger.info(f"Database pool stats: {stats}")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

# Health check function
def health_check() -> dict:
    """Perform database health check"""
    try:
        connection_ok = test_database_connection()
        stats = get_database_stats()
        
        return {
            "status": "healthy" if connection_ok else "unhealthy",
            "connection_ok": connection_ok,
            "pool_stats": stats,
            "database_type": "SQLite" if USE_SQLITE else "PostgreSQL",
            "pool_size_configured": POOL_SIZE if not USE_SQLITE else "N/A"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "connection_ok": False
        }

# Usage tracking utilities
def reset_monthly_usage_counters():
    """Reset monthly usage counters for all users (run monthly)"""
    try:
        with get_db_session() as db:
            current_month = datetime.now(timezone.utc).strftime("%Y-%m")
            
            # Reset user counters
            users = db.query(User).all()
            for user in users:
                # Only reset if it's a new month
                last_reset = user.last_usage_reset or datetime.now(timezone.utc)
                if last_reset.strftime("%Y-%m") != current_month:
                    user.monthly_trim_count = 0
                    user.monthly_hook_count = 0
                    user.last_usage_reset = datetime.now(timezone.utc)
            
            db.commit()
            logger.info(f"Monthly usage counters reset for {len(users)} users")
            
    except Exception as e:
        logger.error(f"Error resetting monthly usage counters: {e}")
        raise

def cleanup_expired_api_keys():
    """Clean up expired API keys"""
    try:
        with get_db_session() as db:
            from models import APIKey
            now = datetime.now(timezone.utc)
            
            expired_keys = db.query(APIKey).filter(
                APIKey.expires_at < now,
                APIKey.is_active == True
            ).all()
            
            for key in expired_keys:
                key.is_active = False
            
            db.commit()
            logger.info(f"Deactivated {len(expired_keys)} expired API keys")
            
    except Exception as e:
        logger.error(f"Error cleaning up expired API keys: {e}")
        raise

def get_usage_analytics(user_id: int = None, days: int = 30) -> dict:
    """Get usage analytics for a user or all users"""
    try:
        with get_db_session() as db:
            from models import UsageLog, VideoJob
            from sqlalchemy import func
            
            # Date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            query = db.query(UsageLog).filter(
                UsageLog.created_at >= start_date,
                UsageLog.created_at <= end_date
            )
            
            if user_id:
                query = query.filter(UsageLog.user_id == user_id)
            
            # Get usage counts by action type
            usage_by_type = query.with_entities(
                UsageLog.action_type,
                func.count(UsageLog.id).label('count')
            ).group_by(UsageLog.action_type).all()
            
            # Get job completion stats
            job_query = db.query(VideoJob).filter(
                VideoJob.created_at >= start_date,
                VideoJob.created_at <= end_date
            )
            
            if user_id:
                job_query = job_query.filter(VideoJob.user_id == user_id)
            
            job_stats = job_query.with_entities(
                VideoJob.status,
                func.count(VideoJob.id).label('count')
            ).group_by(VideoJob.status).all()
            
            return {
                "period": {"start": start_date, "end": end_date, "days": days},
                "usage_by_type": {stat.action_type: stat.count for stat in usage_by_type},
                "job_stats": {stat.status: stat.count for stat in job_stats},
                "user_id": user_id
            }
            
    except Exception as e:
        logger.error(f"Error getting usage analytics: {e}")
        return {"error": str(e)}

def maintenance_cleanup():
    """Perform routine database maintenance"""
    try:
        logger.info("Starting database maintenance...")
        
        # Clean up expired API keys
        cleanup_expired_api_keys()
        
        # Clean up old temporary files (if tracking in DB)
        with get_db_session() as db:
            from models import VideoJob
            
            # Mark old failed/completed jobs for cleanup
            old_date = datetime.now(timezone.utc) - timedelta(days=7)
            old_jobs = db.query(VideoJob).filter(
                VideoJob.updated_at < old_date,
                VideoJob.status.in_(["completed", "failed"])
            ).count()
            
            logger.info(f"Found {old_jobs} old jobs that could be archived")
        
        logger.info("Database maintenance completed")
        
    except Exception as e:
        logger.error(f"Error during database maintenance: {e}")
        raise

if __name__ == "__main__":
    init_db()
    print("Database health check:", health_check())
    
    # Run maintenance if requested
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--maintenance":
        maintenance_cleanup()