# MySQL Setup Instructions - Quick Start

## ✅ What's Already Done
- All code has been migrated from PostgreSQL to MySQL
- Dependencies are configured in `requirements.txt`
- `.env` file has the MySQL connection string
- Database driver changed from `asyncpg` to `aiomysql`

## 🚀 Next Steps (Choose One Method)

### Method 1: Using MySQL Command Line (Recommended)

1. **Connect to MySQL server:**
   ```bash
   mysql -h db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com -u admin -p
   ```
   When prompted, enter password: `cMgoIYsgrGYlTt23LVVq`

2. **Create the database:**
   ```sql
   CREATE DATABASE `prontivus_clinic` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   EXIT;
   ```

3. **Run migrations:**
   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Test the application:**
   ```bash
   uvicorn main:app --reload
   ```

### Method 2: Using AWS RDS Console

1. **Go to AWS RDS Console:**
   - Navigate to your RDS instance: `db-prontivus`
   - Click on "Query Editor" or use a database client

2. **Create database:**
   ```sql
   CREATE DATABASE `prontivus_clinic` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

3. **Run migrations from your local machine:**
   ```bash
   cd backend
   alembic upgrade head
   ```

### Method 3: Using Python Script (If MySQL client not available)

1. **Install MySQL client library:**
   ```bash
   pip install mysql-connector-python
   ```

2. **Run this Python script:**
   ```python
   import mysql.connector
   
   conn = mysql.connector.connect(
       host="db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com",
       user="admin",
       password="cMgoIYsgrGYlTt23LVVq"
   )
   cursor = conn.cursor()
   cursor.execute("CREATE DATABASE IF NOT EXISTS `prontivus_clinic` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
   conn.commit()
   cursor.close()
   conn.close()
   print("Database created!")
   ```

3. **Then run migrations:**
   ```bash
   alembic upgrade head
   ```

## 📋 Verification Checklist

After completing the steps above:

- [ ] Database `prontivus_clinic` exists
- [ ] Migrations ran successfully (`alembic upgrade head`)
- [ ] Application starts without errors
- [ ] Can access API docs at `http://localhost:8000/docs`
- [ ] Database connection works

## 🌐 Production Deployment (Render.com)

1. **Update Environment Variable in Render:**
   - Go to Render Dashboard → Your Backend Service → Environment
   - Update `DATABASE_URL` to:
     ```
     mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
     ```

2. **Deploy:**
   - Push your code to Git
   - Render will automatically:
     - Install dependencies
     - Run `alembic upgrade head` (included in build command)
     - Start the application

## 🔍 Troubleshooting

### Error: "Unknown database 'prontivus_clinic'"
**Solution:** Create the database first using one of the methods above.

### Error: "Access denied for user"
**Solution:** 
- Verify credentials are correct
- Check if your IP is allowed in RDS security group
- Ensure RDS instance is publicly accessible (if connecting from outside AWS)

### Error: "Connection timeout"
**Solution:**
- Check RDS security group allows connections on port 3306
- Verify network connectivity
- Check if RDS instance is running

### Error: "No module named 'aiomysql'"
**Solution:**
```bash
pip install -r requirements.txt
```

## 📝 Important Notes

- **Database Charset:** Using `utf8mb4` for full UTF-8 support (including emojis)
- **UUID Fields:** Now stored as `CHAR(36)` strings instead of native UUID type
- **Connection Pooling:** Configured for optimal performance
- **SQL Mode:** Strict mode enabled for data integrity

## ✅ Success Indicators

You'll know everything is working when:
- ✅ `alembic upgrade head` completes without errors
- ✅ Application starts and shows "Database engine created successfully"
- ✅ API endpoints respond correctly
- ✅ You can create users and clinics
- ✅ No database connection errors in logs

