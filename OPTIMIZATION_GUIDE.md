# Backend & Server-Side Optimization Guide

## Current Status

### ✅ Already Implemented

1. **Redis Caching Infrastructure**
   - `CacheManager` class for async Redis operations
   - `AnalyticsCache` with memory fallback
   - `@cached` decorator for function-level caching
   - Location: `backend/app/core/cache.py`

2. **Database Indexes**
   - Performance indexes migration: `2025_12_12_1343-add_performance_indexes.py`
   - Indexes on: users, patients, appointments, invoices, clinical_records, stock_movements
   - Composite indexes for common query patterns

3. **Connection Pooling**
   - Configured pool size: 25 connections
   - Max overflow: 35 connections
   - Pool timeout: 5 seconds
   - Connection recycling: 2 hours
   - Pre-ping enabled for connection health checks

4. **Query Optimization**
   - Parallel query execution with `asyncio.gather()`
   - Timeout protection on slow queries
   - Graceful degradation with default values

## Optimization Recommendations

### 1. Enable Redis Caching

**Current Status**: Redis infrastructure exists but requires configuration

**Action Required**:
```bash
# Add to backend/.env
REDIS_URL=redis://localhost:6379/0
# Or for production (Render/Heroku):
REDIS_URL=redis://your-redis-host:6379/0
```

**Benefits**:
- Reduce database load by 60-80%
- Faster response times for cached endpoints
- Better scalability

**Endpoints to Cache**:
- ✅ Dashboard stats (already cached - 5 min TTL)
- ✅ User settings (already cached - 5 min TTL)
- ✅ Notifications (already cached - 2 min TTL)
- ⚠️ Add: Patient lists, appointment lists, clinic data

### 2. Enhance Caching Strategy

**Current Issues**:
- `AnalyticsCache` only uses memory (not Redis)
- Redis is async but `AnalyticsCache` is sync

**Recommended Fix**:
```python
# Enhance AnalyticsCache to use Redis via background tasks
# Or migrate to async cache_manager directly
```

### 3. Database Query Optimization

**Already Optimized**:
- ✅ Indexes on frequently queried columns
- ✅ Parallel query execution
- ✅ Query timeouts

**Additional Recommendations**:
- Add composite indexes for common WHERE clauses
- Use `select_related` / `joinedload` for eager loading
- Implement query result pagination
- Add database query logging in development

### 4. Code Optimization

**Current Optimizations**:
- ✅ Async/await throughout
- ✅ Connection pooling
- ✅ Parallel query execution

**Additional Recommendations**:
- Profile slow endpoints with `cProfile` or `py-spy`
- Optimize serialization (Pydantic models)
- Reduce N+1 query problems
- Implement lazy loading for relationships

### 5. Browser Caching (Frontend)

**HTTP Headers to Add**:
```python
# In FastAPI middleware
response.headers["Cache-Control"] = "public, max-age=300"  # 5 minutes
response.headers["ETag"] = generate_etag(response_data)
```

**Static Assets**:
- Enable CDN for static files
- Use versioned filenames for cache busting
- Compress assets (gzip/brotli)

### 6. Database Maintenance

**Regular Tasks**:
```sql
-- Analyze tables for query planner
ANALYZE users;
ANALYZE patients;
ANALYZE appointments;

-- Vacuum (PostgreSQL)
VACUUM ANALYZE;

-- Check index usage
SELECT * FROM pg_stat_user_indexes;
```

**Monitoring**:
- Track slow queries (>1 second)
- Monitor connection pool usage
- Check index hit rates

## Implementation Priority

### High Priority (Immediate)
1. ✅ Configure Redis URL
2. ✅ Enable Redis caching for all endpoints
3. ✅ Add HTTP cache headers

### Medium Priority (This Week)
4. ✅ Enhance AnalyticsCache to use Redis
5. ✅ Add composite database indexes
6. ✅ Implement query result pagination

### Low Priority (This Month)
7. ✅ Profile and optimize slow endpoints
8. ✅ Set up database monitoring
9. ✅ Implement CDN for static assets

## Performance Targets

- **API Response Time**: < 200ms (cached), < 1s (uncached)
- **Database Query Time**: < 100ms (indexed queries)
- **Cache Hit Rate**: > 70%
- **Connection Pool Usage**: < 80% capacity

## Monitoring

### Metrics to Track
- API response times (p50, p95, p99)
- Database query times
- Cache hit/miss rates
- Connection pool usage
- Error rates (4xx, 5xx)

### Tools
- Application logs (structured logging)
- Database query logs
- Redis monitoring
- APM tools (Sentry, New Relic)

