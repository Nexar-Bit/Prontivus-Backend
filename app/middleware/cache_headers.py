"""
Middleware to add HTTP cache headers for better browser caching
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import hashlib


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add cache headers to responses based on endpoint type
    Improves browser caching and reduces server load
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Don't cache error responses
        if response.status_code >= 400:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
        
        # Determine cache strategy based on endpoint
        path = request.url.path
        
        # Static assets - long cache (1 year)
        if path.startswith("/static/") or any(path.endswith(ext) for ext in (".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".woff", ".woff2")):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        
        # API endpoints - smart caching
        elif path.startswith("/api/"):
            # Analytics and dashboard - 5 minutes (private, requires auth)
            if "/analytics/" in path or "/dashboard/" in path:
                response.headers["Cache-Control"] = "private, max-age=300, must-revalidate"
                response.headers["Vary"] = "Authorization"
            
            # Settings and user data - 2 minutes (private, requires auth)
            elif "/settings/" in path or "/auth/me" in path or "/auth/verify-token" in path:
                response.headers["Cache-Control"] = "private, max-age=120, must-revalidate"
                response.headers["Vary"] = "Authorization"
            
            # Notifications - 30 seconds (private, requires auth)
            elif "/notifications" in path:
                response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"
                response.headers["Vary"] = "Authorization"
            
            # Public endpoints (login, register) - 1 minute
            elif "/auth/login" in path or "/auth/register" in path:
                response.headers["Cache-Control"] = "public, max-age=60"
            
            # Other API endpoints - no cache (dynamic data)
            else:
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
                response.headers["Pragma"] = "no-cache"
        
        # Health check endpoints - short cache
        elif "/health" in path or "/ping" in path:
            response.headers["Cache-Control"] = "public, max-age=60"
        
        # Default - no cache
        else:
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        
        return response

