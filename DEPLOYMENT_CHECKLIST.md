# Deployment Checklist - MySQL Migration

## ✅ Pre-Deployment Checklist

### Local Testing
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Test database connection
- [ ] Start application: `uvicorn main:app --reload`
- [ ] Verify API docs at http://localhost:8000/docs
- [ ] Test login endpoint
- [ ] Test clinic creation
- [ ] Check logs for any errors

### Code Verification
- [x] Database driver: `aiomysql` configured
- [x] Connection string: MySQL format
- [x] UUID fields: Converted to CHAR(36)
- [x] Migrations: Applied to head
- [x] Environment variables: Configured

## 🚀 Production Deployment (Render.com)

### Step 1: Update Environment Variables

1. Go to **Render Dashboard** → Your backend service (`prontivus-backend`)
2. Navigate to **Environment** tab
3. Update `DATABASE_URL`:
   ```
   mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
   ```

### Step 2: Verify Other Environment Variables

Ensure these are set in Render:
- `SECRET_KEY` - Strong secret key for JWT
- `BACKEND_CORS_ORIGINS` - `https://prontivus-frontend-p2rr.vercel.app`
- `ENVIRONMENT` - `production`
- `DEBUG` - `false`
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
- `FRONTEND_URL` - `https://prontivus-frontend-p2rr.vercel.app`

### Step 3: Deploy

1. **Commit and push your changes:**
   ```bash
   git add .
   git commit -m "Migrate from PostgreSQL to MySQL"
   git push origin main
   ```

2. **Render will automatically:**
   - Install dependencies from `requirements.txt`
   - Run `alembic upgrade head` (included in build command)
   - Start the application

### Step 4: Verify Deployment

1. **Check Render logs for:**
   - ✅ "Database engine created successfully"
   - ✅ "Application startup complete"
   - ✅ No database connection errors

2. **Test production endpoints:**
   - Health: `https://prontivus-backend-8ef1.onrender.com/api/v1/health`
   - API Docs: `https://prontivus-backend-8ef1.onrender.com/docs`
   - Login: `https://prontivus-backend-8ef1.onrender.com/api/v1/auth/login`

3. **Test from frontend:**
   - Verify frontend can connect to backend
   - Test user login
   - Test clinic creation
   - Verify all features work

## 🔍 Post-Deployment Verification

### Database Connection
- [ ] Application starts without database errors
- [ ] API endpoints respond correctly
- [ ] Database queries execute successfully

### Functionality Tests
- [ ] User authentication works
- [ ] Clinic creation works
- [ ] Patient management works
- [ ] Appointments work
- [ ] Financial features work
- [ ] Clinical records work

### Performance
- [ ] Response times are acceptable
- [ ] No connection pool exhaustion
- [ ] Database queries are optimized

## 🐛 Troubleshooting

### Issue: Application won't start
**Check:**
- Environment variables are set correctly
- `DATABASE_URL` is correct
- Dependencies are installed
- RDS security group allows connections

### Issue: Database connection errors
**Check:**
- MySQL server is running
- Credentials are correct
- Network connectivity
- Security group rules

### Issue: Migration errors
**Solution:**
- Database is already at head revision
- No need to run migrations again
- If needed, use `alembic stamp head` to mark as current

### Issue: UUID-related errors
**Solution:**
- Remember UUIDs are now strings (CHAR(36))
- Use string comparison: `if license_id == "some-uuid-string"`
- Convert UUID objects: `str(uuid.uuid4())`

## 📝 Important Notes

1. **Database**: MySQL 8.0.43 on AWS RDS
2. **Charset**: utf8mb4 (full UTF-8 support)
3. **UUID Storage**: CHAR(36) strings
4. **Connection Pooling**: Configured for optimal performance
5. **SQL Mode**: Strict mode enabled

## ✅ Success Criteria

You'll know deployment is successful when:
- ✅ Application starts without errors
- ✅ All API endpoints respond
- ✅ Database operations work correctly
- ✅ Frontend can connect and function
- ✅ No errors in application logs

---

**Ready to deploy!** 🚀

