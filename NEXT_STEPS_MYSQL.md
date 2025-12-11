# Next Steps: MySQL Migration

## ✅ Completed Changes
- Database driver updated (asyncpg → aiomysql)
- Connection strings updated
- UUID fields converted to CHAR(36)
- Database configuration updated
- Alembic configuration updated

## 🚀 Immediate Next Steps

### Step 1: Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

This will install:
- `aiomysql>=0.3.2` (MySQL async driver)
- `pymysql>=1.1.2` (MySQL sync driver)

### Step 2: Set Environment Variable

**Option A: Add to `.env` file** (recommended for local development)
```bash
# Create or update backend/.env
DATABASE_URL=mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
```

**Option B: Export in terminal** (temporary)
```bash
export DATABASE_URL="mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic"
```

### Step 3: Create Database (if needed)
```bash
python setup_mysql.py
```

This script will:
- Connect to MySQL server
- Create `prontivus_clinic` database if it doesn't exist
- Test the connection
- Display connection details

**Expected Output:**
```
============================================================
Prontivus MySQL Database Setup
============================================================
Connecting to MySQL server at db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com...
✓ Database 'prontivus_clinic' created successfully!

Testing connection to database 'prontivus_clinic'...
✓ Successfully connected to MySQL!
  MySQL Version: 8.0.x
  Database Charset: utf8mb4
  Database Collation: utf8mb4_unicode_ci
```

### Step 4: Run Database Migrations
```bash
alembic upgrade head
```

This will:
- Create all tables
- Set up indexes
- Apply all schema changes

**Note:** If you see any errors about existing tables, you may need to:
- Drop and recreate the database (for fresh start)
- Or manually fix migration conflicts

### Step 5: Test the Application
```bash
# Start the development server
uvicorn main:app --reload
```

**Test endpoints:**
1. Health check: `http://localhost:8000/api/v1/health`
2. API docs: `http://localhost:8000/docs`
3. Login endpoint: `http://localhost:8000/api/v1/auth/login`

## 🌐 Production Deployment (Render.com)

### Step 1: Update Environment Variables in Render Dashboard

1. Go to your Render dashboard
2. Select your backend service (`prontivus-backend`)
3. Go to **Environment** tab
4. Update `DATABASE_URL`:
   ```
   DATABASE_URL=mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
   ```

### Step 2: Deploy

The `render.yaml` already includes `alembic upgrade head` in the build command, so:
1. Push your changes to your Git repository
2. Render will automatically:
   - Install dependencies
   - Run migrations
   - Start the application

### Step 3: Verify Deployment

1. Check Render logs for:
   - ✅ "Database engine created successfully"
   - ✅ "Running migrations..."
   - ✅ "Application startup complete"

2. Test production endpoints:
   - Health: `https://prontivus-backend-8ef1.onrender.com/api/v1/health`
   - API docs: `https://prontivus-backend-8ef1.onrender.com/docs`

## 🔍 Verification Checklist

After completing the steps above, verify:

- [ ] Database connection works
- [ ] Migrations completed successfully
- [ ] All tables created
- [ ] Application starts without errors
- [ ] API endpoints respond correctly
- [ ] UUID fields work correctly (stored as CHAR(36))
- [ ] Can create/login users
- [ ] Can create clinics

## 🐛 Troubleshooting

### Issue: "No module named 'aiomysql'"
**Solution:** Run `pip install -r requirements.txt`

### Issue: "Access denied for user"
**Solution:** 
- Verify MySQL credentials
- Check if MySQL server allows connections from your IP
- Verify database name is correct

### Issue: "Table already exists" during migration
**Solution:**
- For fresh start: Drop and recreate database
- For existing data: Review migration conflicts and fix manually

### Issue: "Connection timeout"
**Solution:**
- Check MySQL server is running
- Verify network connectivity
- Check firewall rules allow port 3306

### Issue: "UUID comparison errors"
**Solution:**
- Remember UUIDs are now strings (CHAR(36))
- Use string comparison: `if license_id == "some-uuid-string"`
- Convert UUID objects to strings: `str(uuid.uuid4())`

## 📝 Important Notes

1. **UUID Handling**: UUIDs are now stored as `CHAR(36)` strings. When accessing them in Python, they'll be strings, not UUID objects.

2. **Character Encoding**: Database uses `utf8mb4` charset for full UTF-8 support (including emojis).

3. **SQL Mode**: MySQL is configured with strict mode for data integrity.

4. **Connection Pooling**: Connection pool settings are configured for optimal performance.

## 🎯 Success Criteria

You'll know the migration is successful when:
- ✅ Application starts without database errors
- ✅ All API endpoints respond correctly
- ✅ You can create users and clinics
- ✅ Database queries execute successfully
- ✅ No PostgreSQL-specific errors in logs

## 📚 Additional Resources

- Full migration guide: `MYSQL_MIGRATION.md`
- Database setup script: `setup_mysql.py`
- Alembic documentation: https://alembic.sqlalchemy.org/

