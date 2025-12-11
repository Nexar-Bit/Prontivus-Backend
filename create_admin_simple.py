"""
Simple script to create initial SuperAdmin using mysql-connector-python
This avoids async/aiomysql issues
"""
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("Installing mysql-connector-python...")
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python", "-q"])
    import mysql.connector
    from mysql.connector import Error

import bcrypt

# MySQL connection details
MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

# Default SuperAdmin credentials
SUPERADMIN_USERNAME = "superadmin"
SUPERADMIN_EMAIL = "admin@prontivus.com"
SUPERADMIN_PASSWORD = "Admin@123456"

print("=" * 60)
print("Creating Initial SuperAdmin User")
print("=" * 60)

try:
    # Connect to MySQL
    print(f"Connecting to MySQL database...")
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    if connection.is_connected():
        cursor = connection.cursor()
        
        # Check if SuperAdmin user already exists (check by username or ADMIN role)
        cursor.execute("SELECT id FROM users WHERE username = %s OR (role = 'ADMIN' AND username LIKE 'super%')", (SUPERADMIN_USERNAME,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  SuperAdmin user already exists (ID: {existing[0]})")
            print("   You can use the existing account to log in.")
            cursor.close()
            connection.close()
            exit(0)
        
        # Check if any clinic exists
        cursor.execute("SELECT id FROM clinics LIMIT 1")
        clinic = cursor.fetchone()
        
        clinic_id = None
        if clinic:
            clinic_id = clinic[0]
            print(f"✓ Found existing clinic (ID: {clinic_id})")
        else:
            print("⚠️  No clinic found. Creating default clinic...")
            # Try with minimal required fields first
            try:
                cursor.execute("""
                    INSERT INTO clinics (name, legal_name, tax_id, email, is_active, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """, ("Sistema Principal", "Sistema Principal", "00000000000000", SUPERADMIN_EMAIL, True))
            except Error as e:
                # If that fails, try with even fewer fields
                if "max_users" in str(e) or "Unknown column" in str(e):
                    cursor.execute("""
                        INSERT INTO clinics (name, legal_name, tax_id, is_active, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                    """, ("Sistema Principal", "Sistema Principal", "00000000000000", True))
                else:
                    raise
            connection.commit()
            clinic_id = cursor.lastrowid
            print(f"✓ Created default clinic (ID: {clinic_id})")
        
        # Check if username/email already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (SUPERADMIN_USERNAME,))
        if cursor.fetchone():
            print(f"❌ Error: Username '{SUPERADMIN_USERNAME}' already exists!")
            cursor.close()
            connection.close()
            exit(1)
        
        cursor.execute("SELECT id FROM users WHERE email = %s", (SUPERADMIN_EMAIL,))
        if cursor.fetchone():
            print(f"❌ Error: Email '{SUPERADMIN_EMAIL}' already exists!")
            cursor.close()
            connection.close()
            exit(1)
        
        # Hash password using bcrypt
        print("Hashing password...")
        hashed_password = bcrypt.hashpw(SUPERADMIN_PASSWORD.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create SuperAdmin user (using role enum, not role_id since table doesn't have it yet)
        print("Creating SuperAdmin user...")
        cursor.execute("""
            INSERT INTO users (
                username, email, hashed_password, first_name, last_name,
                role, clinic_id, is_active, is_verified, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            SUPERADMIN_USERNAME,
            SUPERADMIN_EMAIL,
            hashed_password,
            "Super",
            "Admin",
            "ADMIN",  # Role enum value
            clinic_id,
            True,
            True
        ))
        
        connection.commit()
        user_id = cursor.lastrowid
        
        print("\n" + "=" * 60)
        print("✅ SuperAdmin user created successfully!")
        print("=" * 60)
        print(f"\nLogin Credentials:")
        print(f"  Username: {SUPERADMIN_USERNAME}")
        print(f"  Email: {SUPERADMIN_EMAIL}")
        print(f"  Password: {SUPERADMIN_PASSWORD}")
        print(f"\n⚠️  IMPORTANT: Save these credentials securely!")
        print("   Change the password after first login for security.")
        print("=" * 60)
        
        cursor.close()
        connection.close()
        
except Error as e:
    print(f"\n❌ Error: {e}")
    exit(1)
except Exception as e:
    print(f"\n❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

