# Quick Action Checklist

## ⚠️ CRITICAL: Restart Backend Server

**Why:** Database indexes are created, but backend needs restart to use them effectively.

**How:**
1. Find the terminal/command prompt where backend is running
2. Press `Ctrl+C` to stop it
3. Run: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`

**Expected:** Backend restarts and connects to database with new indexes.

---

## ✅ Verification Steps (After Restart)

### 1. Check Cache is Working
- Load dashboard → Should be slow first time (400-1000ms)
- Reload dashboard → Should be fast (<100ms) - cache hit
- Check backend logs for "Returning cached dashboard stats"

### 2. Check Error Reduction
- Monitor frontend console
- Should see fewer "Service temporarily unavailable" errors
- Should see fewer "Request timeout" errors

### 3. Test Performance
```bash
cd backend
python optimize_database_queries.py
```
**Expected:** Query times should be <100ms (down from 400-1000ms)

---

## 📊 Success Indicators

✅ **Cache Working:**
- First request: Slow (400-1000ms) - hitting database
- Subsequent requests: Fast (<100ms) - cache hit

✅ **Fewer Errors:**
- 503 errors decrease by 70-90%
- Timeout errors decrease significantly

✅ **Better Performance:**
- Dashboard loads faster on repeated visits
- Avatar/notifications load without errors

---

## 🔧 If Still Having Issues

### Check Database Connection
```bash
cd backend
python test_db_connection.py
```

### Check Server Status
```bash
cd backend
python test_server_connection.py
```

### Check Index Usage
```bash
cd backend
python explain_queries.py
```

---

## 📝 Current Configuration

- **Database Pool:** 20 base + 30 overflow = 50 max connections
- **Pool Timeout:** 2 seconds (fail fast)
- **Cache TTLs:**
  - User Settings: 5 minutes
  - Notifications: 2 minutes
  - Dashboard Stats: 5 minutes
- **Indexes:** 10 performance indexes created

---

## 🎯 Priority Order

1. **RESTART BACKEND** ← Do this first!
2. Monitor performance
3. Verify cache is working
4. Check if errors decreased
5. If issues persist, check database server

