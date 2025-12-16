# Quick Fix for Frontend Timeout

## ✅ Backend Status
- Backend is running on port 8000 ✅
- Backend responds quickly (<1s) ✅
- CORS is configured correctly ✅
- Database connection works ✅

## 🔍 Issue
Frontend is getting "Request timeout" errors even though backend is fast.

## 🔧 Quick Fixes

### 1. Check Browser Console
Open browser DevTools (F12) and check:
- **Console tab**: Look for CORS errors or network errors
- **Network tab**: 
  - See if requests are being made
  - Check if requests are pending (hanging)
  - Check response times
  - Look for failed requests (red)

### 2. Check Backend Logs
In the terminal where backend is running, check:
- Are requests arriving? (You should see log entries)
- Are there any errors?
- Are queries taking a long time?

### 3. Test Directly
Open browser and go to:
```
http://localhost:8000/api/v1/analytics/ping
```
Should return: `{"status":"ok"}`

### 4. Check Frontend Port
Make sure frontend is running on:
- `http://localhost:3000` (default Next.js port)
- Or check what port it's actually using

### 5. Restart Both Services
1. **Stop backend** (Ctrl+C in backend terminal)
2. **Stop frontend** (Ctrl+C in frontend terminal)
3. **Restart backend**:
   ```bash
   cd backend
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
4. **Restart frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

## 📊 Expected Behavior
- Backend should show: `INFO:     Uvicorn running on http://0.0.0.0:8000`
- Frontend should show: `- Local: http://localhost:3000`
- Browser console should show successful API calls (not timeouts)

## 🚨 If Still Timing Out
1. Check if you're logged in (need valid JWT token)
2. Check browser Network tab - are requests being made?
3. Check backend logs - are requests arriving?
4. Try accessing dashboard endpoint directly with a valid token

