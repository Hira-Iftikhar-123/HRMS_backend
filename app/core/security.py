from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import os
from typing import List

# Rate limiter configuration
limiter = Limiter(key_func=get_remote_address)

# Security headers middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

# API key validation middleware
class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str = None):
        super().__init__(app)
        self.api_key = api_key or os.getenv("API_KEY")
    
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/", "/docs", "/redoc", "/openapi.json", "/login", "/register", "/health"]
        
        if request.url.path in public_paths:
            return await call_next(request)
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header and api_key_header == self.api_key:
            return await call_next(request)
        
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return await call_next(request)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key or JWT token"
        )

def setup_security_middleware(app: FastAPI):
    """Setup all security middleware for the FastAPI application"""
    
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS protection - restrict to specific origins
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # Trusted hosts - only allow requests from trusted hosts
    trusted_hosts = os.getenv("TRUSTED_HOSTS", "localhost,127.0.0.1,140.245.229.166").split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    
    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # API key protection (optional, can be disabled)
    if os.getenv("ENABLE_API_KEY", "true").lower() == "true":
        app.add_middleware(APIKeyMiddleware)

# Rate limiting decorators for specific endpoints
def rate_limit_public():
    """Rate limit for public endpoints"""
    return limiter.limit("10/minute")

def rate_limit_auth():
    """Rate limit for authentication endpoints"""
    return limiter.limit("5/minute")

def rate_limit_sensitive():
    """Rate limit for sensitive operations"""
    return limiter.limit("30/minute")

def rate_limit_admin():
    """Rate limit for admin operations"""
    return limiter.limit("100/minute")
