"""
Simple script to create MySQL database
Uses mysql-connector-python for reliable connection
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

# MySQL connection details
MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 60)
print("Creating MySQL Database")
print("=" * 60)
print(f"Host: {MYSQL_HOST}")
print(f"Database: {MYSQL_DATABASE}")
print("=" * 60)
print()

try:
    # Connect to MySQL server (without specifying database)
    print(f"Connecting to MySQL server...")
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset='utf8mb4'
    )
    
    if connection.is_connected():
        cursor = connection.cursor()
        
        # Check if database exists
        print(f"Checking if database '{MYSQL_DATABASE}' exists...")
        cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{MYSQL_DATABASE}'")
        exists = cursor.fetchone()
        
        if exists:
            print(f"✓ Database '{MYSQL_DATABASE}' already exists.")
        else:
            print(f"Creating database '{MYSQL_DATABASE}'...")
            # Create database with UTF8MB4 charset
            cursor.execute(f"CREATE DATABASE `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            print(f"✓ Database '{MYSQL_DATABASE}' created successfully!")
        
        # Test connection to the new database
        print(f"\nTesting connection to '{MYSQL_DATABASE}'...")
        cursor.execute(f"USE `{MYSQL_DATABASE}`")
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"✓ MySQL Version: {version}")
        
        cursor.execute("SELECT @@character_set_database, @@collation_database")
        charset, collation = cursor.fetchone()
        print(f"✓ Database Charset: {charset}")
        print(f"✓ Database Collation: {collation}")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✓ SUCCESS! Database is ready.")
        print("=" * 60)
        print("\nNext step: Run migrations")
        print("  alembic upgrade head")
        print("=" * 60)
        
except Error as e:
    print(f"\n✗ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check if MySQL server is accessible")
    print("2. Verify credentials are correct")
    print("3. Check if your IP is allowed in RDS security group")
    print("4. Ensure RDS instance is publicly accessible")
    exit(1)
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")
    exit(1)

