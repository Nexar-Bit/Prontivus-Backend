"""
Script to retrieve all user login information from MySQL database
"""
import mysql.connector
from mysql.connector import Error

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 80)
print("All Users Login Information")
print("=" * 80)

try:
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    if connection.is_connected():
        cursor = connection.cursor(dictionary=True)
        
        # Get all users with their role information
        query = """
            SELECT 
                u.id,
                u.username,
                u.email,
                u.first_name,
                u.last_name,
                u.role,
                ur.name as role_name,
                u.is_active,
                u.is_verified,
                c.name as clinic_name,
                u.clinic_id
            FROM users u
            LEFT JOIN user_roles ur ON u.role_id = ur.id
            LEFT JOIN clinics c ON u.clinic_id = c.id
            ORDER BY u.id
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        print(f"\nTotal Users: {len(users)}\n")
        print("=" * 80)
        
        for idx, user in enumerate(users, 1):
            print(f"\n[{idx}] User ID: {user['id']}")
            print(f"    Username: {user['username']}")
            print(f"    Email: {user['email']}")
            print(f"    Full Name: {user['first_name'] or ''} {user['last_name'] or ''}".strip())
            print(f"    Role (Legacy): {user['role']}")
            print(f"    Role (New): {user['role_name'] or 'N/A'}")
            print(f"    Clinic: {user['clinic_name'] or 'N/A'} (ID: {user['clinic_id']})")
            print(f"    Status: {'Active' if user['is_active'] else 'Inactive'}")
            print(f"    Verified: {'Yes' if user['is_verified'] else 'No'}")
            print(f"    Login: Username='{user['username']}' OR Email='{user['email']}'")
            print("-" * 80)
        
        # Summary by role
        print("\n" + "=" * 80)
        print("Summary by Role")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                COALESCE(ur.name, u.role) as role_name,
                COUNT(*) as count
            FROM users u
            LEFT JOIN user_roles ur ON u.role_id = ur.id
            GROUP BY COALESCE(ur.name, u.role)
            ORDER BY count DESC
        """)
        
        role_summary = cursor.fetchall()
        for role in role_summary:
            print(f"  {role['role_name']}: {role['count']} users")
        
        # Summary by clinic
        print("\n" + "=" * 80)
        print("Summary by Clinic")
        print("=" * 80)
        
        cursor.execute("""
            SELECT 
                c.name as clinic_name,
                COUNT(u.id) as user_count
            FROM clinics c
            LEFT JOIN users u ON c.id = u.clinic_id
            GROUP BY c.id, c.name
            ORDER BY user_count DESC
        """)
        
        clinic_summary = cursor.fetchall()
        for clinic in clinic_summary:
            print(f"  {clinic['clinic_name']}: {clinic['user_count']} users")
        
        print("\n" + "=" * 80)
        print("NOTE: Passwords are hashed and cannot be retrieved.")
        print("Users must use password reset if they forget their password.")
        print("=" * 80)
        
        cursor.close()
        connection.close()
        
except Error as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
except Exception as e:
    print(f"\nFATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

