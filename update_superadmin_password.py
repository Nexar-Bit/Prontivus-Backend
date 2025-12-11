"""
Update superadmin password to admin123
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
print("Updating SuperAdmin Password")
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
    
    # Get current password hash
    cursor.execute("""
        SELECT id, username, email, hashed_password
        FROM users 
        WHERE username = 'superadmin'
    """)
    user = cursor.fetchone()
    
    if not user:
        print("ERROR: SuperAdmin user not found!")
        exit(1)
    
    print(f"\nCurrent SuperAdmin:")
    print(f"  Username: {user['username']}")
    print(f"  Email: {user['email']}")
    
    # Hash the new password
    new_password = "admin123"
    hashed_password = pwd_context.hash(new_password)
    
    print(f"\nUpdating password to: '{new_password}'")
    print(f"New hash: {hashed_password[:50]}...")
    
    # Update password
    cursor.execute("""
        UPDATE users 
        SET hashed_password = %s
        WHERE username = 'superadmin'
    """, (hashed_password,))
    
    conn.commit()
    
    # Verify the update
    cursor.execute("""
        SELECT hashed_password
        FROM users 
        WHERE username = 'superadmin'
    """)
    updated_user = cursor.fetchone()
    
    # Verify the password works
    is_valid = pwd_context.verify(new_password, updated_user['hashed_password'])
    
    if is_valid:
        print("\n✅ Password updated successfully!")
        print(f"✅ Verified: Password '{new_password}' works correctly")
    else:
        print("\n❌ ERROR: Password update failed verification!")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("SuperAdmin Login Credentials:")
    print("=" * 70)
    print(f"Username: superadmin")
    print(f"Email: admin@prontivus.com")
    print(f"Password: {new_password}")
    print("=" * 70)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

