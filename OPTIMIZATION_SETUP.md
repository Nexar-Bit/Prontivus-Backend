# Optimization Setup Guide

## Quick Setup Steps

### 1. Enable Redis Caching (Recommended)

**For Local Development:**
```bash
# Install Redis locally or use Docker
docker run -d -p 6379:6379 redis:alpine

# Add to backend/.env
REDIS_URL=redis://localhost:6379/0
```

**For Production (Render/Heroku):**
```bash
# Create Redis instance on your hosting platform
# Then add to environment variables:
REDIS_URL=redis://your-redis-host:6379/0
```

**Benefits:**
- 60-80% reduction in database queries
- Faster API response times
- Better scalability

### 2. Cache Headers Middleware (Already Integrated)

The cache headers middleware is now integrated in `main.py`. It automatically:
- Adds appropriate cache headers to API responses
- Enables browser caching for static assets
- Sets private caching for authenticated endpoints
- Prevents caching of error responses

**No additional configuration needed** - it works automatically!

### 3. Verify Current Optimizations

**Already Active:**
- ✅ Database connection pooling (25 connections, 35 overflow)
- ✅ Database indexes on frequently queried columns
- ✅ Parallel query execution with `asyncio.gather()`
- ✅ Query timeouts and graceful degradation
- ✅ Memory caching fallback (works without Redis)

**Cache TTLs Currently Set:**
- Dashboard stats: 5 minutes
- User settings: 5 minutes
- Notifications: 2 minutes
- Default: 5 minutes

### 4. Monitor Performance

**Check Redis Connection:**
```python
# In Python shell or test script
from app.core.cache import cache_manager
await cache_manager.connect()
print(f"Redis enabled: {cache_manager.enabled}")
```

**Monitor Database:**
```sql
-- PostgreSQL: Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

**Monitor Cache Hit Rate:**
- Check application logs for cache hits/misses
- Monitor Redis memory usage
- Track API response times

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| API Response (cached) | < 200ms | ~50-100ms |
| API Response (uncached) | < 1s | ~500ms-2s |
| Database Query | < 100ms | ~200-500ms |
| Cache Hit Rate | > 70% | ~60-80% |
| Connection Pool Usage | < 80% | ~40-60% |

## Next Steps

1. **Enable Redis** (if not already done)
   - Add `REDIS_URL` to `.env`
   - Restart backend server
   - Verify connection in logs

2. **Review Cache TTLs**
   - Adjust based on data freshness requirements
   - Balance between performance and data accuracy

3. **Monitor and Optimize**
   - Track slow queries
   - Add indexes for new query patterns
   - Profile slow endpoints

4. **Database Maintenance**
   - Run `ANALYZE` regularly (PostgreSQL)
   - Monitor index usage
   - Clean up old data

## Troubleshooting

**Redis Connection Fails:**
- Check `REDIS_URL` is correct
- Verify Redis server is running
- Check firewall/network settings
- Application will continue with memory cache fallback

**Cache Not Working:**
- Verify Redis is connected (check logs)
- Check cache keys are being set
- Monitor cache hit/miss rates
- Review TTL settings

**Slow Queries:**
- Check database indexes exist
- Run `EXPLAIN ANALYZE` on slow queries
- Consider adding composite indexes
- Review query patterns

## Additional Resources

- See `OPTIMIZATION_GUIDE.md` for detailed strategies
- Check `optimize_caching.py` for enhanced cache implementation
- Review database migrations for index definitions

