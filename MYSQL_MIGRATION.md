# MySQL Migration Guide

This document describes the changes made to migrate Prontivus from PostgreSQL to MySQL.

## Changes Made

### 1. Database Driver
- **Removed**: `asyncpg==0.30.0` (PostgreSQL async driver)
- **Added**: `aiomysql==0.2.0` and `pymysql==1.1.0` (MySQL async drivers)

### 2. Connection Strings
- **Changed from**: `postgresql+asyncpg://user:password@host:5432/database`
- **Changed to**: `mysql+aiomysql://user:password@host:3306/database`

### 3. Database Configuration
- Updated `backend/config.py` default DATABASE_URL
- Updated `backend/database.py` connection string and removed PostgreSQL-specific connection args
- Added MySQL-specific connection args:
  - `charset: utf8mb4` (for full UTF-8 support including emojis)
  - `init_command: SET sql_mode=...` (for strict SQL mode)

### 4. UUID Type Changes
PostgreSQL's native UUID type was replaced with `CHAR(36)` for MySQL compatibility:

**Files Modified:**
- `backend/app/models/__init__.py` - Clinic.license_id
- `backend/app/models/license.py` - License.id and License.activation_key
- `backend/app/models/entitlement.py` - Entitlement.id and Entitlement.license_id
- `backend/app/models/activation.py` - Activation.id and Activation.license_id

**Note**: UUIDs are now stored as strings (CHAR(36)) instead of native UUID type. The `to_dict()` methods already convert UUIDs to strings, so this change is backward compatible.

### 5. Alembic Configuration
- Updated `backend/alembic.ini` with MySQL connection string

## MySQL Database Setup

### Connection Details
- **Host**: `db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com`
- **User**: `admin`
- **Password**: `cMgoIYsgrGYlTt23LVVq`
- **Database**: `prontivus_clinic` (will be created if it doesn't exist)

### Setup Steps

1. **Install Dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Create Database (if needed)**
   ```bash
   python setup_mysql.py
   ```
   This script will:
   - Connect to MySQL server
   - Create the database if it doesn't exist
   - Test the connection
   - Display the DATABASE_URL for environment variables

3. **Set Environment Variable**
   ```bash
   export DATABASE_URL="mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic"
   ```
   
   Or add to `.env` file:
   ```
   DATABASE_URL=mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
   ```

4. **Run Migrations**
   ```bash
   alembic upgrade head
   ```

5. **Test the Application**
   ```bash
   uvicorn main:app --reload
   ```

## Important Notes

### UUID Handling
- UUIDs are now stored as `CHAR(36)` strings in MySQL
- When accessing UUID fields in Python, they will be strings, not UUID objects
- The `to_dict()` methods already handle this correctly
- If you need to compare UUIDs, use string comparison: `license_id == str(uuid_value)`

### Character Encoding
- Database is created with `utf8mb4` charset for full UTF-8 support
- This ensures proper storage of emojis and special characters

### SQL Mode
- MySQL is configured with strict SQL mode for data integrity
- This prevents invalid data from being inserted

### Migration Considerations
- **Existing Data**: If you have existing PostgreSQL data, you'll need to:
  1. Export data from PostgreSQL
  2. Convert UUID columns to strings (CHAR(36))
  3. Import into MySQL
  4. Run migrations to ensure schema matches

- **New Installation**: For fresh installations, simply run the setup script and migrations.

## Production Deployment

For production (Render.com), update the `DATABASE_URL` environment variable in the Render dashboard:

```
DATABASE_URL=mysql+aiomysql://admin:cMgoIYsgrGYlTt23LVVq@db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com/prontivus_clinic
```

The `render.yaml` file already includes `alembic upgrade head` in the build command, so migrations will run automatically on deployment.

## Troubleshooting

### Connection Issues
- Verify MySQL server is accessible from your network
- Check firewall rules allow connections on port 3306
- Verify credentials are correct

### Migration Issues
- Ensure database exists before running migrations
- Check that all dependencies are installed
- Review migration logs for specific errors

### UUID Issues
- Remember UUIDs are now strings, not UUID objects
- Use string comparison: `if license_id == "some-uuid-string"`

## Testing

After migration, test the following:
1. Database connection
2. User authentication
3. Clinic creation
4. License management (UUID fields)
5. All CRUD operations

