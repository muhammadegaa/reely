"""
Middleware components for Reely application
Includes rate limiting, security headers, request logging, and CORS handling
"""
import time
import json
import uuid
import redis
from typing import Callable
from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse
from datetime import datetime, timezone
import logging

from config import settings

# Initialize Redis for rate limiting
try:
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    redis_client.ping()  # Test connection
    redis_available = True
except Exception as e:
    print(f"Redis not available, rate limiting will use in-memory fallback: {e}")
    redis_client = None
    redis_available = False
    # In-memory fallback for development
    rate_limit_storage = {}

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        if settings.enable_security_headers:
            # Security headers
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            
            if settings.is_production:
                # Only in production to avoid HTTPS issues in development
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            
            # Content Security Policy
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.stripe.com https://api.openai.com https://api.anthropic.com; "
                "frame-src https://js.stripe.com https://hooks.stripe.com; "
                "form-action 'self'; "
                "base-uri 'self'"
            )
            response.headers["Content-Security-Policy"] = csp
        
        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with Redis backend"""
    
    def __init__(self, app: FastAPI, requests_per_minute: int = 60, burst_limit: int = 10):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size = 60  # 1 minute window
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for certain endpoints
        skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/payments/webhook"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get client identifier (IP address or API key)
        client_id = self.get_client_id(request)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self.check_rate_limit(client_id)
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Limit: {self.requests_per_minute} requests per minute",
                    "retry_after": reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(self.requests_per_minute),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(reset_time)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)
        
        return response
    
    def get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Check for API key first
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            if token.startswith("rly_"):  # API key format
                return f"api_key:{token[:16]}..."  # Use partial key for identification
        
        # Fallback to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    async def check_rate_limit(self, client_id: str) -> tuple[bool, int, int]:
        """Check if client has exceeded rate limit"""
        current_time = int(time.time())
        window_start = current_time - self.window_size
        
        if redis_available and redis_client:
            return await self._redis_rate_limit(client_id, current_time, window_start)
        else:
            return self._memory_rate_limit(client_id, current_time, window_start)
    
    async def _redis_rate_limit(self, client_id: str, current_time: int, window_start: int) -> tuple[bool, int, int]:
        """Redis-based rate limiting"""
        try:
            pipe = redis_client.pipeline()
            
            # Remove expired entries
            pipe.zremrangebyscore(f"rate_limit:{client_id}", 0, window_start)
            
            # Count current requests
            pipe.zcard(f"rate_limit:{client_id}")
            
            # Add current request
            pipe.zadd(f"rate_limit:{client_id}", {str(uuid.uuid4()): current_time})
            
            # Set expiration
            pipe.expire(f"rate_limit:{client_id}", self.window_size + 10)
            
            results = pipe.execute()
            current_requests = results[1] + 1  # +1 for the request we just added
            
            remaining = max(0, self.requests_per_minute - current_requests)
            reset_time = current_time + self.window_size
            
            is_allowed = current_requests <= self.requests_per_minute
            
            return is_allowed, remaining, reset_time
            
        except Exception as e:
            logger.error(f"Redis rate limiting error: {e}")
            # Fallback to allowing the request
            return True, self.requests_per_minute, current_time + self.window_size
    
    def _memory_rate_limit(self, client_id: str, current_time: int, window_start: int) -> tuple[bool, int, int]:
        """In-memory rate limiting fallback"""
        if client_id not in rate_limit_storage:
            rate_limit_storage[client_id] = []
        
        # Remove expired entries
        rate_limit_storage[client_id] = [
            timestamp for timestamp in rate_limit_storage[client_id]
            if timestamp > window_start
        ]
        
        # Add current request
        rate_limit_storage[client_id].append(current_time)
        
        current_requests = len(rate_limit_storage[client_id])
        remaining = max(0, self.requests_per_minute - current_requests)
        reset_time = current_time + self.window_size
        
        is_allowed = current_requests <= self.requests_per_minute
        
        return is_allowed, remaining, reset_time

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log HTTP requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timer
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # Log request
        logger.info(
            f"Request {request_id}: {request.method} {request.url.path} "
            f"from {client_ip} - {user_agent}"
        )
        
        # Add request ID to request state for access in routes
        request.state.request_id = request_id
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            # Log response
            logger.info(
                f"Response {request_id}: {response.status_code} "
                f"in {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Error {request_id}: {str(e)} in {process_time:.3f}s"
            )
            raise

class AuthenticationLoggingMiddleware(BaseHTTPMiddleware):
    """Log authentication events and track failed attempts"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if this is an auth endpoint
        auth_paths = ["/auth/login", "/auth/register", "/auth/refresh"]
        is_auth_request = any(request.url.path.startswith(path) for path in auth_paths)
        
        response = await call_next(request)
        
        if is_auth_request:
            client_ip = request.client.host if request.client else "unknown"
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                client_ip = forwarded_for.split(",")[0].strip()
            
            if response.status_code == 200:
                # Successful authentication
                logger.info(f"Successful auth: {request.url.path} from {client_ip}")
            elif response.status_code == 401:
                # Failed authentication
                logger.warning(f"Failed auth: {request.url.path} from {client_ip}")
                await self.track_failed_attempt(client_ip)
        
        return response
    
    async def track_failed_attempt(self, client_ip: str):
        """Track failed authentication attempts"""
        if redis_available and redis_client:
            try:
                key = f"failed_auth:{client_ip}"
                current_time = int(time.time())
                
                # Add failed attempt with timestamp
                redis_client.zadd(key, {str(uuid.uuid4()): current_time})
                
                # Remove attempts older than lockout duration
                lockout_seconds = settings.lockout_duration_minutes * 60
                redis_client.zremrangebyscore(key, 0, current_time - lockout_seconds)
                
                # Set expiration
                redis_client.expire(key, lockout_seconds)
                
                # Check if we should lock the IP
                attempt_count = redis_client.zcard(key)
                if attempt_count >= settings.max_login_attempts:
                    logger.warning(f"IP {client_ip} locked due to {attempt_count} failed attempts")
                    
            except Exception as e:
                logger.error(f"Error tracking failed attempt: {e}")

class CacheControlMiddleware(BaseHTTPMiddleware):
    """Add appropriate cache control headers"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Set cache control based on endpoint type
        if request.url.path.startswith("/static/"):
            # Static files - cache for 1 hour
            response.headers["Cache-Control"] = "public, max-age=3600"
        elif request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            # API docs and health - short cache
            response.headers["Cache-Control"] = "public, max-age=300"
        elif request.method == "GET" and response.status_code == 200:
            # GET responses - short cache
            response.headers["Cache-Control"] = "private, max-age=60"
        else:
            # Everything else - no cache
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        
        return response

def setup_middleware(app: FastAPI) -> None:
    """Set up all middleware for the application"""
    
    # Add CORS middleware (should be added first)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    
    # Add trusted host middleware for production
    if settings.is_production:
        allowed_hosts = ["reely.com", "*.reely.com", "api.reely.com"]
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    
    # Add custom middleware in order (last added = first executed)
    app.add_middleware(CacheControlMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(AuthenticationLoggingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.rate_limit_requests_per_minute,
        burst_limit=settings.rate_limit_burst
    )

def check_redis_health() -> dict:
    """Check Redis connection health"""
    if not redis_available or not redis_client:
        return {
            "redis_available": False,
            "error": "Redis not configured or unavailable",
            "fallback": "Using in-memory rate limiting"
        }
    
    try:
        redis_client.ping()
        info = redis_client.info()
        return {
            "redis_available": True,
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        return {
            "redis_available": False,
            "error": str(e),
            "fallback": "Using in-memory rate limiting"
        }

def get_rate_limit_stats(client_id: str) -> dict:
    """Get rate limit statistics for a client"""
    if not redis_available or not redis_client:
        # In-memory fallback
        current_time = int(time.time())
        window_start = current_time - 60
        
        if client_id in rate_limit_storage:
            active_requests = len([
                t for t in rate_limit_storage[client_id]
                if t > window_start
            ])
        else:
            active_requests = 0
        
        return {
            "client_id": client_id,
            "requests_in_window": active_requests,
            "limit": settings.rate_limit_requests_per_minute,
            "remaining": max(0, settings.rate_limit_requests_per_minute - active_requests),
            "window_size": 60,
            "backend": "memory"
        }
    
    try:
        current_time = int(time.time())
        window_start = current_time - 60
        
        # Clean up expired entries
        redis_client.zremrangebyscore(f"rate_limit:{client_id}", 0, window_start)
        
        # Get current count
        current_requests = redis_client.zcard(f"rate_limit:{client_id}")
        
        return {
            "client_id": client_id,
            "requests_in_window": current_requests,
            "limit": settings.rate_limit_requests_per_minute,
            "remaining": max(0, settings.rate_limit_requests_per_minute - current_requests),
            "window_size": 60,
            "backend": "redis"
        }
        
    except Exception as e:
        return {
            "client_id": client_id,
            "error": str(e),
            "backend": "redis"
        }

# Export utility functions
__all__ = [
    "setup_middleware",
    "check_redis_health",
    "get_rate_limit_stats",
    "SecurityHeadersMiddleware",
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "AuthenticationLoggingMiddleware",
    "CacheControlMiddleware"
]