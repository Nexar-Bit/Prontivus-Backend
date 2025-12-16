# MySQL RDS Performance Issue - Root Cause

## 🔴 Root Cause Identified

**Database Location:**
- **AWS RDS MySQL** (db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com)
- **Remote database** (not local)
- **Network latency: ~400ms** per query

**Why PostgreSQL Worked:**
- PostgreSQL was likely:
  - Local database (no network latency)
  - Or better connection/region
  - Or asyncpg driver is more efficient than aiomysql

**Why MySQL is Failing:**
1. **Network Latency:** ~400ms per query (should be <10ms for local)
2. **aiomysql Driver Overhead:** More overhead than asyncpg
3. **Connection Establishment:** Each connection takes time
4. **AWS RDS Overhead:** Additional latency from RDS proxy/load balancer

## ✅ Fixes Applied

### 1. Pool Size Adjusted
- 25 + 35 = 60 connections (matches MySQL limit)
- Prevents connection rejections

### 2. Timeout Optimized
- User lookup: 1.5s timeout
- Fails fast when database is slow

### 3. Caching Increased
- User settings: 5 minutes
- Notifications: 2 minutes
- Dashboard: 5 minutes
- Reduces database queries

### 4. Database Indexes
- 10 performance indexes created
- Should improve query performance

## 🔧 MySQL-Specific Optimizations Needed

### 1. Optimize aiomysql Connection

**Current Issue:**
- Each query takes ~400ms (network latency)
- Connection establishment adds overhead
- aiomysql may have more overhead than asyncpg

**Potential Fixes:**

**A. Use Connection Pooling More Aggressively:**
- Keep connections alive longer
- Reuse connections more
- Reduce connection establishment overhead

**B. Optimize Connection String:**
```python
connect_args={
    "charset": "utf8mb4",
    "init_command": "SET sql_mode='...'",
    "connect_timeout": 10,  # If supported
    "read_timeout": 30,     # If supported
    "write_timeout": 30,    # If supported
}
```

**C. Check aiomysql Version:**
- Ensure latest version for best performance
- Check if there are known performance issues

### 2. AWS RDS Optimization

**Check RDS Instance:**
1. **Instance Type:** Is it t2.micro or t3.micro? (Very slow)
   - Consider upgrading to t3.small or larger
   - Or use db.t3.micro at minimum

2. **Region:** sa-east-1 (São Paulo)
   - If you're connecting from far away, latency increases
   - Consider if your application is in the same region

3. **RDS Performance Insights:**
   - Enable Performance Insights to see slow queries
   - Check CPU, memory, disk I/O metrics

4. **Connection Pooling:**
   - Consider using RDS Proxy (AWS service)
   - Or use ProxySQL for connection pooling

### 3. Network Optimization

**If Database is Remote:**
- Network latency is unavoidable
- Each query round-trip adds ~400ms
- Under load, this compounds

**Solutions:**
1. **Increase Cache TTLs** (already done)
2. **Use Read Replicas** for read-heavy workloads
3. **Optimize Queries** to reduce round-trips
4. **Batch Queries** where possible

## 📊 Comparison: PostgreSQL vs MySQL

**PostgreSQL (Working):**
- ✅ Likely local or better connection
- ✅ asyncpg driver is efficient
- ✅ Low latency (<10ms)
- ✅ No connection issues

**MySQL RDS (Current):**
- ❌ Remote (AWS RDS)
- ❌ ~400ms network latency
- ❌ aiomysql driver overhead
- ❌ Connection establishment overhead
- ❌ Pool exhaustion under load

## 🔧 Immediate Actions

### 1. RESTART BACKEND (Required)
```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Check AWS RDS Instance

**Check RDS Console:**
- Instance type (t2.micro is very slow)
- CPU utilization
- Memory utilization
- Network latency

**Consider:**
- Upgrading instance type
- Enabling Performance Insights
- Using RDS Proxy for connection pooling

### 3. Optimize Connection Handling

**Increase Pool Recycle Time:**
- Keep connections alive longer
- Reduce connection establishment overhead

**Use Connection Pooling:**
- RDS Proxy (AWS service)
- Or application-level pooling (already done)

## 💡 Long-term Solutions

### Option 1: Upgrade RDS Instance
- From t2.micro → t3.small or larger
- Better CPU and network performance
- Reduces query latency

### Option 2: Use RDS Proxy
- AWS-managed connection pooling
- Reduces connection overhead
- Better connection management

### Option 3: Optimize Queries
- Reduce number of queries
- Use batch operations
- Optimize JOIN operations

### Option 4: Use Read Replicas
- Separate read/write traffic
- Reduce load on primary
- Better performance for reads

## 📝 Summary

**Root Cause:**
- MySQL on AWS RDS (remote)
- ~400ms network latency per query
- aiomysql driver overhead
- Connection establishment overhead

**Why PostgreSQL Worked:**
- Likely local or better connection
- asyncpg is more efficient
- Lower latency

**Fixes Applied:**
- ✅ Pool size: 60 (matches MySQL limit)
- ✅ Timeout: 1.5s (fails fast)
- ✅ Caching: Increased TTLs
- ✅ Indexes: 10 performance indexes

**Action Required:**
- ⚠️ **RESTART BACKEND** (applies fixes)
- ⚠️ **CHECK RDS INSTANCE** (may need upgrade)
- ⚠️ **CONSIDER RDS PROXY** (for connection pooling)

**Expected:**
- Fewer 503 errors (pool size fixed)
- Faster failures (timeout reduced)
- Still slow queries (~400ms) - network latency issue

