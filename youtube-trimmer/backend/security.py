"""
Security middleware and utilities for Reely
Includes rate limiting, request validation, and security headers
"""
import time
import hashlib
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Callable, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# In-memory rate limiting store (in production, use Redis)
rate_limit_store: Dict[str, deque] = defaultdict(deque)
api_key_rate_limits: Dict[str, deque] = defaultdict(deque)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with different limits for different user types
    """
    
    def __init__(
        self,
        app,
        default_requests_per_minute: int = 60,
        default_burst_limit: int = 10,
        authenticated_requests_per_minute: int = 120,
        premium_requests_per_minute: int = 300,
        api_key_requests_per_minute: int = 600,
    ):
        super().__init__(app)
        self.default_rpm = default_requests_per_minute
        self.default_burst = default_burst_limit
        self.authenticated_rpm = authenticated_requests_per_minute
        self.premium_rpm = premium_requests_per_minute
        self.api_key_rpm = api_key_requests_per_minute
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for health checks and static files
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get client identifier
        client_id = self.get_client_id(request)
        
        # Determine rate limit based on authentication
        rate_limit = await self.get_rate_limit(request)
        
        # Check rate limit
        current_time = time.time()
        window_start = current_time - 60  # 1-minute window
        
        # Clean old entries
        client_requests = rate_limit_store[client_id]
        while client_requests and client_requests[0] < window_start:
            client_requests.popleft()
        
        # Check if limit exceeded
        if len(client_requests) >= rate_limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Too many requests. Limit: {rate_limit} per minute",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Add current request
        client_requests.append(current_time)
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(rate_limit - len(client_requests))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        
        return response
    
    def get_client_id(self, request: Request) -> str:
        """Get unique client identifier"""
        # Check for API key first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{hashlib.sha256(api_key.encode()).hexdigest()[:16]}"
        
        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            return f"jwt:{hashlib.sha256(token.encode()).hexdigest()[:16]}"
        
        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"
    
    async def get_rate_limit(self, request: Request) -> int:
        """Determine rate limit based on user authentication and subscription"""
        # Check for API key (highest limit)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return self.api_key_rpm
        
        # Check for JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # For now, return authenticated rate limit
            # In a real implementation, you'd decode the JWT and check subscription tier
            return self.authenticated_rpm
        
        # Default rate limit for anonymous users
        return self.default_rpm

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), location=(), payment=()"
        
        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.stripe.com; "
            "frame-src 'none'; "
            "object-src 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for common security issues
    """
    
    def __init__(self, app, max_content_length: int = 100 * 1024 * 1024):  # 100MB
        super().__init__(app)
        self.max_content_length = max_content_length
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_content_length:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"error": "Request too large", "max_size_mb": self.max_content_length // (1024 * 1024)}
            )
        
        # Check for suspicious patterns in URL
        path = request.url.path
        suspicious_patterns = [
            "../", "..\\",  # Path traversal
            "<?php", "<%",  # Script injection attempts
            "SELECT ", "UNION ", "INSERT ", "DELETE ", "DROP ",  # SQL injection
            "<script", "javascript:",  # XSS attempts
        ]
        
        for pattern in suspicious_patterns:
            if pattern.lower() in path.lower():
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"error": "Invalid request"}
                )
        
        return await call_next(request)

# IP blocking functionality
blocked_ips: Dict[str, datetime] = {}
failed_attempts: Dict[str, list] = defaultdict(list)

def is_ip_blocked(ip: str) -> bool:
    """Check if an IP is currently blocked"""
    if ip in blocked_ips:
        if datetime.now(timezone.utc) > blocked_ips[ip]:
            # Block expired, remove it
            del blocked_ips[ip]
            if ip in failed_attempts:
                del failed_attempts[ip]
            return False
        return True
    return False

def record_failed_attempt(ip: str, block_duration_minutes: int = 15):
    """Record a failed authentication attempt"""
    current_time = datetime.now(timezone.utc)
    
    # Clean old attempts (older than 1 hour)
    cutoff_time = current_time - timedelta(hours=1)
    failed_attempts[ip] = [
        attempt_time for attempt_time in failed_attempts[ip]
        if attempt_time > cutoff_time
    ]
    
    # Add current attempt
    failed_attempts[ip].append(current_time)
    
    # Check if should block (5 failed attempts in 1 hour)
    if len(failed_attempts[ip]) >= 5:
        block_until = current_time + timedelta(minutes=block_duration_minutes)
        blocked_ips[ip] = block_until
        print(f"Blocked IP {ip} until {block_until}")

def clear_failed_attempts(ip: str):
    """Clear failed attempts for an IP (on successful login)"""
    if ip in failed_attempts:
        del failed_attempts[ip]

# Request logging for security monitoring
security_log: deque = deque(maxlen=1000)  # Keep last 1000 security events

def log_security_event(event_type: str, ip: str, details: dict = None):
    """Log a security event"""
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        "ip": ip,
        "details": details or {}
    }
    security_log.append(event)

def get_security_stats() -> dict:
    """Get security statistics"""
    current_time = datetime.now(timezone.utc)
    last_hour = current_time - timedelta(hours=1)
    
    recent_events = [
        event for event in security_log
        if datetime.fromisoformat(event["timestamp"]) > last_hour
    ]
    
    event_types = defaultdict(int)
    for event in recent_events:
        event_types[event["type"]] += 1
    
    return {
        "blocked_ips_count": len(blocked_ips),
        "failed_attempts_count": sum(len(attempts) for attempts in failed_attempts.values()),
        "recent_events_count": len(recent_events),
        "event_types": dict(event_types),
        "rate_limit_clients": len(rate_limit_store)
    }

# Input validation utilities
def validate_youtube_url(url: str) -> bool:
    """Validate YouTube URL format"""
    import re
    youtube_patterns = [
        r'https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(www\.)?youtu\.be/[\w-]+',
        r'https?://(www\.)?youtube\.com/embed/[\w-]+',
        r'https?://(www\.)?youtube\.com/v/[\w-]+'
    ]
    
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    import re
    # Remove path separators and other dangerous characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Limit length
    sanitized = sanitized[:100]
    return sanitized or "file"

def validate_timestamp(timestamp: str) -> bool:
    """Validate timestamp format (HH:MM:SS or MM:SS or seconds)"""
    import re
    patterns = [
        r'^\d{1,2}:\d{2}:\d{2}$',  # HH:MM:SS
        r'^\d{1,2}:\d{2}$',        # MM:SS
        r'^\d+$'                   # seconds
    ]
    
    return any(re.match(pattern, timestamp) for pattern in patterns)

# CORS security
def get_cors_origins() -> list:
    """Get allowed CORS origins from environment"""
    import os
    cors_origins = os.getenv("CORS_ORIGINS", "")
    if cors_origins:
        origins = [origin.strip() for origin in cors_origins.split(",")]
        # Validate origins
        valid_origins = []
        for origin in origins:
            if origin.startswith(("http://", "https://")) or origin == "*":
                valid_origins.append(origin)
        return valid_origins
    
    # Default origins for development
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

# Webhook signature validation
def validate_stripe_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Validate Stripe webhook signature"""
    import hmac
    import hashlib
    
    try:
        # Extract timestamp and signatures from header
        elements = signature.split(',')
        timestamp = int(elements[0].split('=')[1])
        signatures = [element.split('=')[1] for element in elements if element.startswith('v1=')]
        
        # Check if timestamp is recent (within 5 minutes)
        current_time = int(time.time())
        if abs(current_time - timestamp) > 300:
            return False
        
        # Create expected signature
        signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            signed_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return any(hmac.compare_digest(expected_signature, sig) for sig in signatures)
        
    except Exception:
        return False

# API key validation
def validate_api_key_format(api_key: str) -> bool:
    """Validate API key format"""
    import re
    # Expected format: rly_live_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    pattern = r'^rly_live_[A-Za-z0-9]{32}$'
    return bool(re.match(pattern, api_key))

# Password strength validation
def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    # Check for common weak passwords
    weak_passwords = [
        "password", "123456", "password123", "admin", "letmein",
        "welcome", "monkey", "1234567890", "qwerty", "abc123"
    ]
    
    if password.lower() in weak_passwords:
        return False, "Password is too common. Please choose a stronger password"
    
    return True, "Password is strong"