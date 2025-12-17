"""
Middleware to add HTTP cache headers for better browser caching
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse
import time


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add cache headers to responses based on endpoint type
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Don't cache error responses
        if response.status_code >= 400:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        
        # Determine cache strategy based on endpoint
        path = request.url.path
        
        # Static assets - long cache
        if path.startswith("/static/") or path.endswith((".js", ".css", ".png", ".jpg", ".svg")):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        
        # API endpoints - short cache
        elif path.startswith("/api/"):
            # Analytics and dashboard - 5 minutes
            if "/analytics/" in path or "/dashboard/" in path:
                response.headers["Cache-Control"] = "private, max-age=300"
                response.headers["Vary"] = "Authorization"
            
            # Settings and user data - 2 minutes
            elif "/settings/" in path or "/auth/me" in path:
                response.headers["Cache-Control"] = "private, max-age=120"
                response.headers["Vary"] = "Authorization"
            
            # Notifications - 30 seconds
            elif "/notifications" in path:
                response.headers["Cache-Control"] = "private, max-age=30"
                response.headers["Vary"] = "Authorization"
            
            # Other API endpoints - no cache
            else:
                response.headers["Cache-Control"] = "no-cache, must-revalidate"
        
        # Add ETag for cache validation
        if isinstance(response, Response):
            # Generate simple ETag from response content hash
            if hasattr(response, 'body'):
                import hashlib
                etag = hashlib.md5(response.body).hexdigest()
                response.headers["ETag"] = f'"{etag}"'
        
        return response

