"""
Fix all users to have proper role_id based on their legacy role
"""
import mysql.connector

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Fixing Missing role_id for All Users")
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
    
    # Get role mappings
    cursor.execute("SELECT id, name FROM user_roles")
    roles = {role['name']: role['id'] for role in cursor.fetchall()}
    
    print("\nRole mappings:")
    for name, role_id in roles.items():
        print(f"  {name}: {role_id}")
    
    # Map legacy roles to new role IDs
    role_mapping = {
        'ADMIN': roles.get('SuperAdmin', 1),  # Default to SuperAdmin if AdminClinica doesn't exist
        'DOCTOR': roles.get('Medico', 3),
        'SECRETARY': roles.get('Secretaria', 4),
        'PATIENT': roles.get('Paciente', 5)
    }
    
    # Check for AdminClinica role
    if 'AdminClinica' in roles:
        # For clinic admins, we need to check if they're clinic admins or superadmin
        # SuperAdmin should be ID 1, AdminClinica should be ID 2
        role_mapping['ADMIN'] = roles.get('AdminClinica', 2)
    
    print("\nLegacy role to new role mapping:")
    for legacy, new_id in role_mapping.items():
        role_name = [name for name, rid in roles.items() if rid == new_id][0] if new_id in roles.values() else 'Unknown'
        print(f"  {legacy} -> {role_name} (ID: {new_id})")
    
    # Get all users without role_id or with NULL role_id
    cursor.execute("""
        SELECT id, username, email, role, role_id, clinic_id
        FROM users
        WHERE role_id IS NULL
    """)
    users_to_fix = cursor.fetchall()
    
    print(f"\nFound {len(users_to_fix)} users without role_id")
    
    # Special handling: Check if user is SuperAdmin (clinic_id = 1 and username = superadmin)
    # vs AdminClinica (other clinics)
    updated = 0
    for user in users_to_fix:
        role_id = None
        
        # Determine role_id based on legacy role
        if user['role'] == 'ADMIN':
            # Check if this is the superadmin user
            if user['username'] == 'superadmin' or user['email'] == 'admin@prontivus.com':
                role_id = roles.get('SuperAdmin', 1)
            else:
                # Clinic admin
                role_id = roles.get('AdminClinica', 2)
        elif user['role'] in role_mapping:
            role_id = role_mapping[user['role']]
        
        if role_id:
            cursor.execute("""
                UPDATE users 
                SET role_id = %s 
                WHERE id = %s
            """, (role_id, user['id']))
            updated += 1
            print(f"  Updated {user['username']} ({user['role']}) -> role_id={role_id}")
        else:
            print(f"  WARNING: Could not determine role_id for {user['username']} (role: {user['role']})")
    
    conn.commit()
    
    print(f"\n✅ Updated {updated} users with role_id")
    
    # Verify
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE role_id IS NULL")
    remaining = cursor.fetchone()['count']
    print(f"  Remaining users without role_id: {remaining}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("Fix Complete!")
    print("=" * 70)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

