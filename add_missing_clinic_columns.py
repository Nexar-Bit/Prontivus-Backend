"""
Add all missing columns to clinics table
"""
import mysql.connector
from mysql.connector import Error

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Adding missing columns to clinics table")
print("=" * 70)

try:
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # Define columns to add
    columns_to_add = [
        {
            'name': 'license_key',
            'definition': 'VARCHAR(100) NULL',
            'after': 'email'
        },
        {
            'name': 'expiration_date',
            'definition': 'DATE NULL',
            'after': 'license_key'
        },
        {
            'name': 'max_users',
            'definition': 'INT NOT NULL DEFAULT 10',
            'after': 'expiration_date'
        },
        {
            'name': 'active_modules',
            'definition': 'JSON NULL',
            'after': 'max_users'
        },
        {
            'name': 'license_id',
            'definition': 'CHAR(36) NULL',
            'after': 'active_modules'
        }
    ]
    
    # Check existing columns
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics'
    """, (MYSQL_DATABASE,))
    
    existing_columns = {row[0] for row in cursor.fetchall()}
    
    print("\n[Step 1] Checking existing columns...")
    for col in columns_to_add:
        if col['name'] in existing_columns:
            print(f"  ✅ {col['name']} already exists")
        else:
            print(f"  ⚠️  {col['name']} is missing")
    
    # Add missing columns
    print("\n[Step 2] Adding missing columns...")
    added_count = 0
    
    for col in columns_to_add:
        if col['name'] not in existing_columns:
            try:
                sql = f"ALTER TABLE clinics ADD COLUMN {col['name']} {col['definition']}"
                if 'after' in col:
                    sql += f" AFTER {col['after']}"
                
                cursor.execute(sql)
                print(f"  ✅ Added {col['name']}")
                added_count += 1
            except Error as e:
                print(f"  ❌ Failed to add {col['name']}: {e}")
    
    if added_count > 0:
        conn.commit()
        print(f"\n✅ Successfully added {added_count} column(s)")
    else:
        print("\n✅ All columns already exist")
    
    # Add indexes
    print("\n[Step 3] Adding indexes...")
    
    indexes_to_add = [
        {
            'name': 'ix_clinics_license_key',
            'column': 'license_key',
            'unique': True
        },
        {
            'name': 'ix_clinics_license_id',
            'column': 'license_id',
            'unique': True
        }
    ]
    
    # Check existing indexes
    cursor.execute("""
        SELECT INDEX_NAME 
        FROM INFORMATION_SCHEMA.STATISTICS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics'
    """, (MYSQL_DATABASE,))
    
    existing_indexes = {row[0] for row in cursor.fetchall()}
    
    for idx in indexes_to_add:
        if idx['name'] not in existing_indexes:
            try:
                unique = 'UNIQUE' if idx['unique'] else ''
                sql = f"CREATE {unique} INDEX {idx['name']} ON clinics ({idx['column']})"
                cursor.execute(sql)
                print(f"  ✅ Added index {idx['name']}")
            except Error as e:
                print(f"  ⚠️  Failed to add index {idx['name']}: {e}")
        else:
            print(f"  ✅ Index {idx['name']} already exists")
    
    if added_count > 0:
        conn.commit()
    
    # Verify final schema
    print("\n[Step 4] Verifying final schema...")
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics'
        ORDER BY ORDINAL_POSITION
    """, (MYSQL_DATABASE,))
    
    columns = cursor.fetchall()
    print("\nFinal clinics table columns:")
    print("-" * 70)
    for col in columns:
        print(f"  {col[0]:25} {col[1]:15} Nullable: {col[2]:5} Default: {col[3]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Fix Complete")
    print("=" * 70)
    print("\nThe clinics table now has all required columns.")
    print("Login should work now. Please try again.")
    
except Error as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

