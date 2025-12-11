# Quick Start - MySQL Migration

## Current Status ✅
- ✅ All code migrated to MySQL
- ✅ Dependencies configured
- ✅ Environment variables set

## Immediate Next Steps

### 1. Create Database (Choose One)

**Option A: MySQL Command Line**
```bash
mysql -h db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com -u admin -p
# Password: cMgoIYsgrGYlTt23LVVq
```
Then run:
```sql
CREATE DATABASE `prontivus_clinic` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;
```

**Option B: Use SQL File**
```bash
mysql -h db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com -u admin -p < create_database.sql
# Password: cMgoIYsgrGYlTt23LVVq
```

**Option C: AWS RDS Query Editor**
- Open AWS RDS Console
- Select your instance
- Use Query Editor
- Run the SQL from `create_database.sql`

### 2. Run Migrations
```bash
cd backend
alembic upgrade head
```

### 3. Test Application
```bash
uvicorn main:app --reload
```

Visit: http://localhost:8000/docs

## Production (Render.com)

1. **Update DATABASE_URL in Render Dashboard:**
   ```
   mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
   ```

2. **Push to Git** - Render will auto-deploy and run migrations

## Need Help?

- See `MYSQL_SETUP_INSTRUCTIONS.md` for detailed troubleshooting
- See `MYSQL_MIGRATION.md` for technical details

