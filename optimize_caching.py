"""
Script to enhance AnalyticsCache to use Redis via async operations
This bridges the gap between sync AnalyticsCache and async Redis
"""
import asyncio
from typing import Optional, Any
from app.core.cache import cache_manager, AnalyticsCache


class EnhancedAnalyticsCache(AnalyticsCache):
    """
    Enhanced cache that uses Redis via async operations
    Falls back to memory cache if Redis is unavailable
    """
    
    def __init__(self):
        super().__init__()
        self._redis_enabled = False
        self._check_redis()
    
    def _check_redis(self):
        """Check if Redis is available"""
        if cache_manager.enabled:
            self._redis_enabled = True
    
    def get(self, key: str) -> Optional[Any]:
        """Get from cache (memory first, then Redis if available)"""
        # Check memory cache first (fastest)
        result = super().get(key)
        if result is not None:
            return result
        
        # Try Redis if available (async operation in sync context)
        if self._redis_enabled and cache_manager.redis_client:
            try:
                # Run async operation in sync context
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, create a task
                    # Note: This is a simplified approach
                    # For production, consider using a thread pool
                    return None  # Fallback to None if loop is running
                else:
                    result = loop.run_until_complete(cache_manager.get(key))
                    if result:
                        # Also store in memory cache for faster access
                        self.set(key, result, ttl_seconds=300)
                    return result
            except Exception:
                # If Redis fails, fall back to memory cache
                return None
        
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set in cache (memory and Redis if available)"""
        # Always store in memory cache
        super().set(key, value, ttl_seconds)
        
        # Also store in Redis if available (async operation)
        if self._redis_enabled and cache_manager.redis_client:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(
                        cache_manager.set(key, value, ttl=ttl_seconds)
                    )
            except Exception:
                # If Redis fails, memory cache still works
                pass
    
    def delete(self, key: str):
        """Delete from cache (memory and Redis)"""
        super().delete(key)
        
        if self._redis_enabled and cache_manager.redis_client:
            try:
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    loop.run_until_complete(cache_manager.delete(key))
            except Exception:
                pass


# Replace analytics_cache with enhanced version
# Note: This should be done after cache_manager.connect() is called
def init_enhanced_cache():
    """Initialize enhanced cache after Redis connection"""
    global analytics_cache
    analytics_cache = EnhancedAnalyticsCache()

