"""
Check superadmin password hash and verify which password is correct
"""
import mysql.connector
from passlib.context import CryptContext

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

# Initialize password context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("=" * 70)
print("Checking SuperAdmin Password")
print("=" * 70)

try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    cursor = conn.cursor(dictionary=True)
    
    # Get superadmin user
    cursor.execute("""
        SELECT id, username, email, hashed_password, created_at
        FROM users 
        WHERE username = 'superadmin' OR email = 'admin@prontivus.com'
    """)
    user = cursor.fetchone()
    
    if not user:
        print("ERROR: SuperAdmin user not found!")
        exit(1)
    
    print(f"\nSuperAdmin User:")
    print(f"  ID: {user['id']}")
    print(f"  Username: {user['username']}")
    print(f"  Email: {user['email']}")
    print(f"  Created At: {user['created_at']}")
    print(f"  Password Hash: {user['hashed_password'][:50]}...")
    
    # Test passwords
    passwords_to_test = [
        "admin123",
        "Admin@123456",
        "Admin123",
        "admin@123456",
        "Admin123456"
    ]
    
    print("\n" + "=" * 70)
    print("Testing Passwords")
    print("=" * 70)
    
    correct_password = None
    for password in passwords_to_test:
        try:
            is_valid = pwd_context.verify(password, user['hashed_password'])
            status = "✅ CORRECT" if is_valid else "❌ Incorrect"
            print(f"\n{password:20} -> {status}")
            if is_valid:
                correct_password = password
        except Exception as e:
            print(f"\n{password:20} -> ERROR: {e}")
    
    print("\n" + "=" * 70)
    if correct_password:
        print(f"✅ CORRECT PASSWORD FOUND: '{correct_password}'")
    else:
        print("❌ None of the tested passwords match!")
        print("\nThe password hash in the database doesn't match any of the tested passwords.")
        print("You may need to reset the password.")
    
    print("=" * 70)
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

