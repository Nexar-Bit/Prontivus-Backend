"""
Test the login flow to identify potential issues
Simulates what happens during login
"""
import mysql.connector
from passlib.context import CryptContext

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

print("=" * 70)
print("Testing Login Flow")
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
    
    # Step 1: Authenticate user
    print("\n[Step 1] Authenticating user...")
    username_or_email = "superadmin"
    password = "admin123"
    
    cursor.execute("""
        SELECT id, username, email, hashed_password, role_id, clinic_id, is_active, is_verified
        FROM users 
        WHERE username = %s OR email = %s
    """, (username_or_email, username_or_email))
    user = cursor.fetchone()
    
    if not user:
        print("  ERROR: User not found!")
        exit(1)
    
    print(f"  OK: User found - {user['username']}")
    
    # Verify password
    if not pwd_context.verify(password, user['hashed_password']):
        print("  ERROR: Password incorrect!")
        exit(1)
    
    print("  OK: Password verified")
    
    # Step 2: Check user role
    print("\n[Step 2] Getting user role...")
    if not user['role_id']:
        print("  ERROR: User has no role_id!")
        exit(1)
    
    cursor.execute("SELECT id, name FROM user_roles WHERE id = %s", (user['role_id'],))
    role = cursor.fetchone()
    
    if not role:
        print(f"  ERROR: Role ID {user['role_id']} not found!")
        exit(1)
    
    print(f"  OK: Role found - {role['name']}")
    
    # Step 3: Check clinic
    print("\n[Step 3] Getting clinic...")
    cursor.execute("SELECT id, name FROM clinics WHERE id = %s", (user['clinic_id'],))
    clinic = cursor.fetchone()
    
    if not clinic:
        print(f"  ERROR: Clinic ID {user['clinic_id']} not found!")
        exit(1)
    
    print(f"  OK: Clinic found - {clinic['name']}")
    
    # Step 4: Get menu items for role
    print("\n[Step 4] Getting menu items for role...")
    cursor.execute("""
        SELECT mi.id, mi.name, mi.route, mi.group_id
        FROM menu_items mi
        INNER JOIN role_menu_permissions rmp ON mi.id = rmp.menu_item_id
        WHERE rmp.role_id = %s AND mi.is_active = 1
        ORDER BY mi.group_id, mi.order_index
    """, (user['role_id'],))
    menu_items = cursor.fetchall()
    
    print(f"  OK: Found {len(menu_items)} menu items")
    
    # Step 5: Get menu groups
    print("\n[Step 5] Getting menu groups...")
    cursor.execute("""
        SELECT DISTINCT mg.id, mg.name, mg.order_index
        FROM menu_groups mg
        INNER JOIN menu_items mi ON mg.id = mi.group_id
        INNER JOIN role_menu_permissions rmp ON mi.id = rmp.menu_item_id
        WHERE rmp.role_id = %s AND mg.is_active = 1
        ORDER BY mg.order_index
    """, (user['role_id'],))
    menu_groups = cursor.fetchall()
    
    print(f"  OK: Found {len(menu_groups)} menu groups")
    
    # Step 6: Check for any NULL values that could cause issues
    print("\n[Step 6] Checking for potential issues...")
    issues = []
    
    if user['role_id'] is None:
        issues.append("User role_id is NULL")
    if user['clinic_id'] is None:
        issues.append("User clinic_id is NULL")
    if not user['is_active']:
        issues.append("User is inactive")
    
    # Check menu items for NULL values
    for item in menu_items:
        if item['group_id'] is None:
            issues.append(f"Menu item {item['name']} has NULL group_id")
    
    if issues:
        print("  WARNINGS:")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  OK: No issues found")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Login Flow Test: PASSED")
    print("=" * 70)
    print("\nAll checks passed. The login should work.")
    print("\nIf you're still getting a 500 error on Render:")
    print("  1. Check Render logs for the actual error message")
    print("  2. Ensure Render has the latest code deployed")
    print("  3. Verify Render's DATABASE_URL points to the MySQL database")
    print("  4. Check if there are any missing dependencies")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

