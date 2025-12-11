"""
Check the structure of the users table
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

try:
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    cursor = connection.cursor()
    
    # Get table structure
    print("Users table structure:")
    cursor.execute("DESCRIBE users")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[0]} - {col[1]}")
    
    # Check if users table exists and has data
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    print(f"\nTotal users: {count}")
    
    # Check user_roles table
    print("\nUser roles:")
    cursor.execute("SELECT id, name FROM user_roles")
    roles = cursor.fetchall()
    for role in roles:
        print(f"  ID {role[0]}: {role[1]}")
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f"Error: {e}")

