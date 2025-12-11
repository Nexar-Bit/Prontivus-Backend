"""
Script to add missing role_id column to users table in production
This fixes the "Unknown column 'users.role_id'" error
"""
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mysql-connector-python", "-q"])
    import mysql.connector
    from mysql.connector import Error

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 60)
print("Fixing Missing role_id Column")
print("=" * 60)

try:
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    if connection.is_connected():
        cursor = connection.cursor()
        
        # Check if role_id column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'role_id'
        """, (MYSQL_DATABASE,))
        
        if cursor.fetchone():
            print("✓ role_id column already exists")
        else:
            print("⚠️  role_id column missing. Adding it...")
            
            # Check if user_roles table exists first
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_NAME = 'user_roles'
            """, (MYSQL_DATABASE,))
            
            if not cursor.fetchone():
                print("⚠️  user_roles table doesn't exist. Creating it first...")
                # Create user_roles table (basic structure)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_roles (
                        id INTEGER AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(50) NOT NULL UNIQUE,
                        description TEXT,
                        is_system BOOLEAN DEFAULT FALSE,
                        created_at DATETIME DEFAULT NOW(),
                        updated_at DATETIME
                    )
                """)
                
                # Insert default roles
                cursor.execute("""
                    INSERT IGNORE INTO user_roles (id, name, description, is_system) VALUES
                    (1, 'SuperAdmin', 'Super Administrator', TRUE),
                    (2, 'AdminClinica', 'Clinic Administrator', TRUE),
                    (3, 'Medico', 'Doctor', TRUE),
                    (4, 'Secretaria', 'Secretary', TRUE),
                    (5, 'Paciente', 'Patient', TRUE)
                """)
                connection.commit()
                print("✓ Created user_roles table with default roles")
            
            # Add role_id column to users table
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN role_id INTEGER NULL
            """)
            
            # Create index
            try:
                cursor.execute("""
                    CREATE INDEX ix_users_role_id ON users(role_id)
                """)
            except Error as e:
                if "Duplicate key name" not in str(e):
                    print(f"  Note: Index may already exist: {e}")
            
            # Add foreign key constraint
            try:
                cursor.execute("""
                    ALTER TABLE users 
                    ADD CONSTRAINT fk_users_role_id 
                    FOREIGN KEY (role_id) REFERENCES user_roles(id)
                """)
            except Error as e:
                if "Duplicate key name" not in str(e) and "already exists" not in str(e):
                    print(f"  Note: Foreign key may already exist: {e}")
            
            connection.commit()
            print("✓ Added role_id column to users table")
            
            # Update existing users to have role_id based on their role enum
            print("Updating existing users with role_id...")
            cursor.execute("""
                UPDATE users 
                SET role_id = CASE 
                    WHEN role = 'ADMIN' AND username = 'superadmin' THEN 1
                    WHEN role = 'ADMIN' THEN 2
                    WHEN role = 'DOCTOR' THEN 3
                    WHEN role = 'SECRETARY' THEN 4
                    WHEN role = 'PATIENT' THEN 5
                    ELSE 5
                END
                WHERE role_id IS NULL
            """)
            connection.commit()
            updated = cursor.rowcount
            print(f"✓ Updated {updated} users with role_id")
        
        # Check if permissions column exists
        cursor.execute("""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s 
            AND TABLE_NAME = 'users' 
            AND COLUMN_NAME = 'permissions'
        """, (MYSQL_DATABASE,))
        
        if not cursor.fetchone():
            print("⚠️  permissions column missing. Adding it...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN permissions JSON NULL
            """)
            connection.commit()
            print("✓ Added permissions column to users table")
        
        print("\n" + "=" * 60)
        print("✅ Fix completed successfully!")
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

