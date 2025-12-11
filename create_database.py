"""
Simple script to create MySQL database using pymysql (sync)
"""
import pymysql

# MySQL connection details
MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

try:
    # Connect to MySQL server (without specifying database)
    print(f"Connecting to MySQL server at {MYSQL_HOST}...")
    connection = pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset='utf8mb4'
    )
    
    try:
        with connection.cursor() as cursor:
            # Check if database exists
            cursor.execute(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{MYSQL_DATABASE}'")
            exists = cursor.fetchone()
            
            if not exists:
                print(f"Creating database '{MYSQL_DATABASE}'...")
                # Create database with UTF8MB4 charset
                cursor.execute(f"CREATE DATABASE `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                connection.commit()
                print(f"✓ Database '{MYSQL_DATABASE}' created successfully!")
            else:
                print(f"✓ Database '{MYSQL_DATABASE}' already exists.")
            
            # Test connection to the new database
            cursor.execute(f"USE `{MYSQL_DATABASE}`")
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            print(f"✓ MySQL Version: {version}")
            
            cursor.execute("SELECT @@character_set_database, @@collation_database")
            charset, collation = cursor.fetchone()
            print(f"✓ Database Charset: {charset}")
            print(f"✓ Database Collation: {collation}")
            
    finally:
        connection.close()
        
    print("\n" + "=" * 60)
    print("✓ Database setup completed successfully!")
    print("=" * 60)
    print("\nNext step: Run migrations:")
    print("  alembic upgrade head")
    print("=" * 60)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    exit(1)

