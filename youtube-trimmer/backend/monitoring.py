"""
Monitoring and logging system for Reely
Includes metrics collection, health checks, and alerting
"""
import os
import time
import psutil
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from functools import wraps
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import PlainTextResponse
import redis

# Initialize Sentry if DSN is provided
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
            RedisIntegration()
        ],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "development"),
        attach_stacktrace=True,
        send_default_pii=False
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reely.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

VIDEO_PROCESSING_COUNT = Counter(
    'video_processing_total',
    'Total video processing requests',
    ['operation', 'status']
)

VIDEO_PROCESSING_DURATION = Histogram(
    'video_processing_duration_seconds',
    'Video processing duration',
    ['operation']
)

USER_REGISTRATIONS = Counter(
    'user_registrations_total',
    'Total user registrations'
)

SUBSCRIPTION_CHANGES = Counter(
    'subscription_changes_total',
    'Total subscription changes',
    ['tier', 'action']
)

SYSTEM_CPU_USAGE = Gauge('system_cpu_usage_percent', 'System CPU usage percentage')
SYSTEM_MEMORY_USAGE = Gauge('system_memory_usage_percent', 'System memory usage percentage')
SYSTEM_DISK_USAGE = Gauge('system_disk_usage_percent', 'System disk usage percentage')

# Redis connection for caching metrics
try:
    redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    redis_available = True
except Exception as e:
    logger.warning(f"Redis not available for metrics caching: {e}")
    redis_available = False

class MetricsCollector:
    """Collect and store application metrics"""
    
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.processing_jobs = 0
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        self.request_count += 1
        if status_code >= 400:
            self.error_count += 1
    
    def record_video_processing(self, operation: str, status: str, duration: Optional[float] = None):
        """Record video processing metrics"""
        VIDEO_PROCESSING_COUNT.labels(operation=operation, status=status).inc()
        if duration:
            VIDEO_PROCESSING_DURATION.labels(operation=operation).observe(duration)
    
    def record_user_registration(self):
        """Record user registration"""
        USER_REGISTRATIONS.inc()
    
    def record_subscription_change(self, tier: str, action: str):
        """Record subscription change"""
        SUBSCRIPTION_CHANGES.labels(tier=tier, action=action).inc()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Update Prometheus gauges
        SYSTEM_CPU_USAGE.set(cpu_percent)
        SYSTEM_MEMORY_USAGE.set(memory.percent)
        SYSTEM_DISK_USAGE.set(disk.percent)
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": memory.available / (1024**3),
            "disk_percent": disk.percent,
            "disk_free_gb": disk.free / (1024**3),
            "uptime_seconds": time.time() - self.start_time,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "processing_jobs": self.processing_jobs
        }
    
    def get_application_health(self) -> Dict[str, Any]:
        """Get application health status"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development")
        }
        
        # Check database connection
        try:
            from database import SessionLocal
            with SessionLocal() as db:
                db.execute("SELECT 1")
            health_status["database"] = "healthy"
        except Exception as e:
            health_status["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Redis connection
        if redis_available:
            try:
                redis_client.ping()
                health_status["redis"] = "healthy"
            except Exception as e:
                health_status["redis"] = f"unhealthy: {str(e)}"
                health_status["status"] = "degraded"
        else:
            health_status["redis"] = "not_configured"
        
        # Check external services
        health_status["openai"] = "configured" if os.getenv("OPENAI_API_KEY") else "not_configured"
        health_status["anthropic"] = "configured" if os.getenv("ANTHROPIC_API_KEY") else "not_configured"
        health_status["stripe"] = "configured" if os.getenv("STRIPE_SECRET_KEY") else "not_configured"
        
        # Check system resources
        system_metrics = self.get_system_metrics()
        if system_metrics["cpu_percent"] > 90 or system_metrics["memory_percent"] > 90:
            health_status["status"] = "degraded"
            health_status["warning"] = "High resource usage"
        
        return health_status

# Global metrics collector
metrics_collector = MetricsCollector()

class MonitoringMiddleware:
    """Middleware for collecting request metrics and monitoring"""
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        start_time = time.time()
        
        # Increment active connections
        ACTIVE_CONNECTIONS.inc()
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            # Add performance headers
            response.headers["X-Process-Time"] = str(round(duration, 4))
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            metrics_collector.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=500,
                duration=duration
            )
            
            # Log error with context
            logger.error(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "duration": duration,
                    "client_ip": request.client.host,
                    "user_agent": request.headers.get("user-agent"),
                    "error": str(e)
                }
            )
            raise
        
        finally:
            # Decrement active connections
            ACTIVE_CONNECTIONS.dec()

def monitor_performance(operation: str):
    """Decorator for monitoring function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_video_processing(operation, "success", duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_video_processing(operation, "error", duration)
                logger.error(f"{operation} failed after {duration:.2f}s: {str(e)}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metrics_collector.record_video_processing(operation, "success", duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metrics_collector.record_video_processing(operation, "error", duration)
                logger.error(f"{operation} failed after {duration:.2f}s: {str(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Monitoring endpoints
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)

async def health_endpoint():
    """Health check endpoint"""
    health = metrics_collector.get_application_health()
    status_code = 200 if health["status"] == "healthy" else 503
    return Response(content=health, status_code=status_code)

async def detailed_health_endpoint():
    """Detailed health check with system metrics"""
    health = metrics_collector.get_application_health()
    system_metrics = metrics_collector.get_system_metrics()
    
    detailed_health = {
        **health,
        "system_metrics": system_metrics
    }
    
    status_code = 200 if health["status"] == "healthy" else 503
    return Response(content=detailed_health, status_code=status_code)

# Alerting system
class AlertManager:
    """Simple alerting for critical issues"""
    
    def __init__(self):
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "cpu_usage": 90,    # 90% CPU usage
            "memory_usage": 90, # 90% memory usage
            "disk_usage": 85    # 85% disk usage
        }
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes between alerts
    
    def check_and_alert(self):
        """Check metrics and send alerts if thresholds exceeded"""
        current_time = time.time()
        system_metrics = metrics_collector.get_system_metrics()
        
        # Check error rate
        if system_metrics["error_rate"] > self.alert_thresholds["error_rate"]:
            self._send_alert(
                "high_error_rate",
                f"High error rate: {system_metrics['error_rate']:.2%}",
                current_time
            )
        
        # Check system resources
        for metric, threshold in [
            ("cpu_percent", "cpu_usage"),
            ("memory_percent", "memory_usage"),
            ("disk_percent", "disk_usage")
        ]:
            if system_metrics[metric] > self.alert_thresholds[threshold]:
                self._send_alert(
                    f"high_{threshold}",
                    f"High {metric}: {system_metrics[metric]:.1f}%",
                    current_time
                )
    
    def _send_alert(self, alert_type: str, message: str, current_time: float):
        """Send alert (log for now, could be extended to email/Slack/etc)"""
        last_alert = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_alert > self.alert_cooldown:
            logger.critical(f"ALERT [{alert_type}]: {message}")
            self.last_alert_time[alert_type] = current_time
            
            # Could extend to send to external alerting systems
            # self._send_to_slack(message)
            # self._send_email_alert(message)

# Global alert manager
alert_manager = AlertManager()

# Background task for periodic monitoring
async def monitoring_background_task():
    """Background task that runs monitoring checks"""
    while True:
        try:
            alert_manager.check_and_alert()
            
            # Cache metrics in Redis if available
            if redis_available:
                try:
                    system_metrics = metrics_collector.get_system_metrics()
                    redis_client.setex(
                        "metrics:system",
                        300,  # 5 minutes TTL
                        str(system_metrics)
                    )
                except Exception as e:
                    logger.warning(f"Failed to cache metrics: {e}")
            
        except Exception as e:
            logger.error(f"Monitoring background task error: {e}")
        
        await asyncio.sleep(60)  # Run every minute

def setup_monitoring(app: FastAPI):
    """Set up monitoring for FastAPI application"""
    
    # Add monitoring middleware
    app.add_middleware(MonitoringMiddleware)
    
    # Add monitoring endpoints
    app.add_api_route("/metrics", metrics_endpoint, methods=["GET"], tags=["Monitoring"])
    app.add_api_route("/health", health_endpoint, methods=["GET"], tags=["Monitoring"])
    app.add_api_route("/health/detailed", detailed_health_endpoint, methods=["GET"], tags=["Monitoring"])
    
    # Start background monitoring task
    @app.on_event("startup")
    async def start_monitoring():
        asyncio.create_task(monitoring_background_task())
        logger.info("Monitoring system started")
    
    logger.info("Monitoring middleware and endpoints configured")