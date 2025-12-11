# Initial Setup - Creating First Admin User

## ⚠️ Important: Login Information is NOT the Same

**The MySQL database is NEW and EMPTY** - no users exist from the old PostgreSQL database.

You need to create the initial SuperAdmin user to access the system.

## 🚀 Quick Setup

### Option 1: Use the Setup Script (Recommended)

```bash
cd backend
python create_initial_admin.py
```

The script will:
1. Check if SuperAdmin role exists
2. Create a default clinic if needed
3. Prompt you for SuperAdmin credentials
4. Create the SuperAdmin user

**Example:**
```
Username [superadmin]: superadmin
Email [admin@prontivus.com]: admin@prontivus.com
Password (min 8 chars): YourSecurePassword123
```

### Option 2: Create via API (After First User)

Once you have a SuperAdmin, you can:
1. Log in with SuperAdmin credentials
2. Create clinics via `/api/v1/admin/clinics` endpoint
3. Each clinic creation automatically creates an AdminClinica user

### Option 3: Manual SQL (Advanced)

If you prefer to create the user manually via SQL:

```sql
-- First, ensure you have a clinic (or create one)
INSERT INTO clinics (name, legal_name, tax_id, email, is_active, max_users, created_at)
VALUES ('Sistema Principal', 'Sistema Principal', '00000000000000', 'admin@prontivus.com', true, 1000, NOW());

-- Get the clinic ID (replace 1 with actual clinic ID)
-- Then create SuperAdmin user (role_id = 1 is SuperAdmin)
INSERT INTO users (username, email, hashed_password, first_name, last_name, role, role_id, clinic_id, is_active, is_verified, created_at)
VALUES (
    'superadmin',
    'admin@prontivus.com',
    '$2b$12$...',  -- Use bcrypt hash of your password
    1,  -- SuperAdmin role_id
    1,  -- Clinic ID
    true,
    true,
    NOW()
);
```

**Note:** You'll need to generate the bcrypt hash for the password. Use the Python script instead - it's easier!

## 📋 After Creating SuperAdmin

1. **Log in** with the credentials you created
2. **Create clinics** via the admin panel
3. **Each clinic** will automatically get an AdminClinica user with credentials sent via email

## 🔄 If You Need to Migrate Data from PostgreSQL

If you have existing users in PostgreSQL that you want to migrate:

1. **Export data** from PostgreSQL:
   ```sql
   -- Export users table
   COPY users TO '/path/to/users.csv' WITH CSV HEADER;
   ```

2. **Import to MySQL** (adjust as needed):
   ```sql
   -- Import users (you'll need to adjust UUID fields to CHAR(36))
   LOAD DATA INFILE '/path/to/users.csv' INTO TABLE users ...;
   ```

3. **Update UUID fields** from PostgreSQL UUID format to MySQL CHAR(36) format

**Note:** This is a complex process. For a fresh start, it's easier to just create a new SuperAdmin and recreate clinics/users.

## ✅ Verification

After creating SuperAdmin, verify:
1. Can log in at `/api/v1/auth/login`
2. Can access admin endpoints
3. Can create clinics
4. Can manage users

---

**Remember:** The MySQL database is fresh - you need to create all users/clinics from scratch (or migrate data from PostgreSQL if you have it).

