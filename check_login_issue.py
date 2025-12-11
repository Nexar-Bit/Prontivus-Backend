"""
Check potential login issues after MySQL migration
"""
import mysql.connector

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Checking Login Endpoint Requirements")
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
    
    # Check superadmin user
    print("\n[1] Checking SuperAdmin user...")
    cursor.execute("""
        SELECT id, username, email, role_id, clinic_id, is_active, is_verified
        FROM users 
        WHERE username = 'superadmin' OR email = 'admin@prontivus.com'
    """)
    user = cursor.fetchone()
    if user:
        print(f"  OK: User found (ID: {user['id']})")
        print(f"  Role ID: {user['role_id']}")
        print(f"  Clinic ID: {user['clinic_id']}")
    else:
        print("  ERROR: SuperAdmin user not found!")
    
    # Check role exists
    print("\n[2] Checking user role...")
    if user and user['role_id']:
        cursor.execute("SELECT id, name FROM user_roles WHERE id = %s", (user['role_id'],))
        role = cursor.fetchone()
        if role:
            print(f"  OK: Role found - {role['name']}")
        else:
            print(f"  ERROR: Role ID {user['role_id']} not found!")
    
    # Check clinic exists
    print("\n[3] Checking clinic...")
    if user and user['clinic_id']:
        cursor.execute("SELECT id, name FROM clinics WHERE id = %s", (user['clinic_id'],))
        clinic = cursor.fetchone()
        if clinic:
            print(f"  OK: Clinic found - {clinic['name']}")
        else:
            print(f"  ERROR: Clinic ID {user['clinic_id']} not found!")
    
    # Check menu tables
    print("\n[4] Checking menu tables...")
    cursor.execute("SELECT COUNT(*) as count FROM menu_groups")
    menu_groups = cursor.fetchone()['count']
    print(f"  Menu Groups: {menu_groups}")
    
    cursor.execute("SELECT COUNT(*) as count FROM menu_items")
    menu_items = cursor.fetchone()['count']
    print(f"  Menu Items: {menu_items}")
    
    cursor.execute("SELECT COUNT(*) as count FROM role_menu_permissions")
    role_perms = cursor.fetchone()['count']
    print(f"  Role-Menu Permissions: {role_perms}")
    
    # Check if SuperAdmin has menu permissions
    print("\n[5] Checking SuperAdmin menu permissions...")
    if user and user['role_id']:
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM role_menu_permissions 
            WHERE role_id = %s
        """, (user['role_id'],))
        perm_count = cursor.fetchone()['count']
        print(f"  SuperAdmin has {perm_count} menu permissions")
        if perm_count == 0:
            print("  WARNING: SuperAdmin has no menu permissions!")
    
    # Check for users with missing role_id
    print("\n[6] Checking users with missing role_id...")
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role_id IS NULL")
    missing_role = cursor.fetchone()['count']
    print(f"  Users without role_id: {missing_role}")
    if missing_role > 0:
        cursor.execute("SELECT id, username, email FROM users WHERE role_id IS NULL LIMIT 5")
        users_no_role = cursor.fetchall()
        print("  Examples:")
        for u in users_no_role:
            print(f"    - {u['username']} ({u['email']})")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("Check Complete")
    print("=" * 70)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

