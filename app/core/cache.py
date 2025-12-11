"""
Redis caching utilities for improved performance
"""
import os
import json
from typing import Optional, Any, Dict
import redis.asyncio as redis
from functools import wraps
import hashlib


class CacheManager:
    """Redis cache manager for async operations"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = False
    
    async def connect(self):
        """Connect to Redis"""
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                self.redis_client = await redis.from_url(
                    redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                # Test connection
                await self.redis_client.ping()
                self.enabled = True
            except Exception as e:
                print(f"⚠️  Redis connection failed: {e}. Continuing without cache.")
                self.enabled = False
        else:
            print("ℹ️  Redis URL not configured. Caching disabled.")
            self.enabled = False
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis_client:
            await self.redis_client.close()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled or not self.redis_client:
            return None
        
        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL (default 1 hour)"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
            return True
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return False


# Global cache manager instance
cache_manager = CacheManager()


class AnalyticsCache:
    """
    Synchronous cache adapter for analytics endpoints
    Wraps the async CacheManager for synchronous use
    """
    def __init__(self):
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._use_redis = False
    
    def _init_redis(self):
        """Initialize Redis connection if available"""
        if cache_manager.enabled and cache_manager.redis_client:
            self._use_redis = True
    
    def get(self, key: str) -> Optional[Any]:
        """
        Synchronous get from cache
        Uses memory cache (works in both sync and async contexts)
        Redis is accessed via async cache_manager when available
        """
        # Check memory cache first (always works)
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            from datetime import datetime
            if datetime.now().timestamp() < expiry:
                return value
            else:
                # Expired, remove it
                del self._memory_cache[key]
        
        # Note: Redis access is async, so we rely on memory cache for sync access
        # The async cache_manager will be used by async endpoints directly
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """
        Synchronous set to cache
        Stores in memory cache (works in both sync and async contexts)
        Redis is accessed via async cache_manager when available
        """
        from datetime import datetime, timedelta
        expiry = (datetime.now() + timedelta(seconds=ttl_seconds)).timestamp()
        
        # Store in memory cache (always works)
        self._memory_cache[key] = (value, expiry)
        
        # Note: Redis storage is async, so we rely on memory cache for sync access
        # The async cache_manager will be used by async endpoints directly
    
    def delete(self, key: str):
        """Delete a specific key from cache"""
        if key in self._memory_cache:
            del self._memory_cache[key]
    
    def clear(self):
        """Clear all cached data"""
        self._memory_cache.clear()


# Analytics cache instance (synchronous interface)
analytics_cache = AnalyticsCache()


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_data = {
        "args": str(args),
        "kwargs": str(sorted(kwargs.items()))
    }
    key_string = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_string.encode()).hexdigest()


def cached(ttl: int = 3600, key_prefix: str = ""):
    """
    Decorator to cache function results
    
    Usage:
        @cached(ttl=1800, key_prefix="patients")
        async def get_patients(db: AsyncSession):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_str = f"{key_prefix}:{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key_str)
            if cached_result is not None:
                return cached_result
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache_manager.set(cache_key_str, result, ttl)
            
            return result
        return wrapper
    return decorator
