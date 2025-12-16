# AWS RDS MySQL Optimization Guide

## 🔴 Current Situation

**Database:** AWS RDS MySQL 8.0.43
**Location:** sa-east-1 (São Paulo)
**Issue:** ~400ms latency per query (network + RDS overhead)

## ✅ Code Optimizations Applied

1. **Pool Size:** 25 + 35 = 60 (matches MySQL limit)
2. **Pool Recycle:** 3600s → 7200s (2 hours, matches RDS wait_timeout)
3. **Pool Pre-Ping:** Enabled (keeps connections alive)
4. **Caching:** Increased TTLs to reduce queries
5. **Indexes:** 10 performance indexes created

## 🔧 AWS RDS Optimizations

### 1. Check RDS Instance Type

**Current:** Unknown (check in AWS Console)

**Recommendations:**
- **Minimum:** db.t3.small (2 vCPU, 2GB RAM)
- **Recommended:** db.t3.medium (2 vCPU, 4GB RAM) or larger
- **Avoid:** db.t2.micro (very slow, not suitable for production)

**To Check:**
1. Go to AWS RDS Console
2. Select your database instance
3. Check "Instance class" in Configuration tab

**To Upgrade:**
1. RDS Console → Modify
2. Change "DB instance class"
3. Apply during maintenance window (or immediately with downtime)

### 2. Enable Performance Insights

**Benefits:**
- See slow queries
- Identify bottlenecks
- Monitor database performance

**Steps:**
1. RDS Console → Modify
2. Enable "Performance Insights"
3. Set retention (7 days is free tier)

### 3. Use RDS Proxy (Recommended)

**Benefits:**
- Connection pooling at AWS level
- Reduces connection overhead
- Better connection management
- Automatic failover

**Steps:**
1. RDS Console → Proxies → Create proxy
2. Select your RDS instance
3. Configure connection pooling
4. Update DATABASE_URL to use proxy endpoint

**Connection String:**
```
mysql+aiomysql://user:password@your-proxy-endpoint.proxy-xxxxx.sa-east-1.rds.amazonaws.com:3306/prontivus_clinic
```

### 4. Check RDS Parameter Group

**Important Parameters:**
```sql
-- Check current values
SHOW VARIABLES LIKE 'innodb_buffer_pool_size';
SHOW VARIABLES LIKE 'max_connections';
SHOW VARIABLES LIKE 'wait_timeout';
```

**Optimize:**
- `innodb_buffer_pool_size`: Should be 70-80% of instance RAM
- `max_connections`: Should be >= 60 (your pool size)
- `wait_timeout`: 28800 (8 hours) is fine

### 5. Network Optimization

**If Application is in Different Region:**
- Consider moving application to sa-east-1
- Or use CloudFront/CDN for static assets
- Or use VPC peering if both in AWS

**Check Network Latency:**
```bash
# Test latency to RDS
ping db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com
```

## 📊 Expected Performance

**Current (Remote RDS):**
- Query latency: ~400ms
- Connection overhead: High
- Pool exhaustion: Under load

**After Optimizations:**
- Query latency: Still ~400ms (network limitation)
- But fewer queries (caching)
- Better connection reuse (pool recycle)
- Fewer 503 errors (pool size fixed)

**With RDS Proxy:**
- Connection overhead: Reduced
- Better connection management
- Automatic failover
- Still ~400ms query latency (network)

**With Instance Upgrade:**
- Query latency: May improve slightly
- Better CPU/memory for complex queries
- Still network latency (if remote)

## 🚨 Critical Actions

### 1. RESTART BACKEND (Required)
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Check RDS Instance Type
- Go to AWS Console
- Check if it's t2.micro (very slow)
- Consider upgrading if needed

### 3. Consider RDS Proxy
- Reduces connection overhead
- Better for connection pooling
- Easy to set up

## 💡 Why PostgreSQL Worked

**Likely Reasons:**
1. **Local Database:** PostgreSQL was probably local (no network latency)
2. **Better Driver:** asyncpg is more efficient than aiomysql
3. **Better Connection:** Lower latency connection
4. **No RDS Overhead:** Direct connection vs RDS proxy

**MySQL RDS Issues:**
1. **Remote:** Network latency (~400ms)
2. **RDS Overhead:** Additional latency from AWS
3. **aiomysql:** More overhead than asyncpg
4. **Connection Establishment:** Takes time for each connection

## 📝 Summary

**Root Cause:**
- AWS RDS MySQL (remote database)
- ~400ms network latency
- aiomysql driver overhead
- Connection establishment overhead

**Fixes Applied:**
- ✅ Pool size: 60 (matches MySQL)
- ✅ Pool recycle: 7200s (2 hours)
- ✅ Caching: Increased TTLs
- ✅ Indexes: 10 performance indexes

**Action Required:**
- ⚠️ **RESTART BACKEND** (applies fixes)
- ⚠️ **CHECK RDS INSTANCE** (may need upgrade)
- ⚠️ **CONSIDER RDS PROXY** (for connection pooling)

**Expected:**
- Fewer 503 errors (pool size fixed)
- Better connection reuse (pool recycle increased)
- Still ~400ms query latency (network limitation)

