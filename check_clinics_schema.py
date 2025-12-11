"""
Check clinics table schema to ensure all columns match the model
"""
import mysql.connector

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Checking clinics table schema")
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
    
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics'
        ORDER BY ORDINAL_POSITION
    """, (MYSQL_DATABASE,))
    
    columns = cursor.fetchall()
    
    print("\nCurrent clinics table columns:")
    print("-" * 70)
    for col in columns:
        print(f"  {col['COLUMN_NAME']:25} {col['DATA_TYPE']:15} "
              f"Length: {str(col['CHARACTER_MAXIMUM_LENGTH']):5} "
              f"Nullable: {col['IS_NULLABLE']}")
    
    # Check for required columns
    required_columns = {
        'id': 'int',
        'name': 'varchar',
        'legal_name': 'varchar',
        'commercial_name': 'varchar',
        'tax_id': 'varchar',
        'address': 'text',
        'phone': 'varchar',
        'email': 'varchar',
        'license_key': 'varchar',
        'expiration_date': 'date',
        'max_users': 'int',
        'active_modules': 'json',
        'license_id': 'char',
        'is_active': 'tinyint',
        'created_at': 'datetime',
        'updated_at': 'datetime'
    }
    
    existing_columns = {col['COLUMN_NAME']: col['DATA_TYPE'] for col in columns}
    
    print("\n" + "=" * 70)
    print("Schema Check:")
    print("=" * 70)
    
    missing = []
    for col_name, expected_type in required_columns.items():
        if col_name not in existing_columns:
            missing.append(col_name)
            print(f"  ❌ Missing: {col_name}")
        else:
            actual_type = existing_columns[col_name]
            if col_name == 'license_id' and actual_type == 'char':
                print(f"  ✅ {col_name:25} (correct type: {actual_type})")
            elif col_name == 'license_id' and actual_type != 'char':
                print(f"  ⚠️  {col_name:25} (wrong type: {actual_type}, should be char(36))")
            else:
                print(f"  ✅ {col_name:25} ({actual_type})")
    
    if missing:
        print(f"\n⚠️  Missing columns: {', '.join(missing)}")
    else:
        print("\n✅ All required columns are present!")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

