"""
Fix clinics table - add missing commercial_name column
"""
import mysql.connector
from mysql.connector import Error

MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Fixing clinics table - Adding missing commercial_name column")
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
    
    # Check if column already exists
    cursor.execute("""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics' 
        AND COLUMN_NAME = 'commercial_name'
    """, (MYSQL_DATABASE,))
    
    exists = cursor.fetchone()
    
    if exists:
        print("\n✅ Column 'commercial_name' already exists in clinics table")
    else:
        print("\n[Step 1] Adding commercial_name column to clinics table...")
        cursor.execute("""
            ALTER TABLE clinics 
            ADD COLUMN commercial_name VARCHAR(200) NULL 
            AFTER legal_name
        """)
        conn.commit()
        print("  ✅ Column added successfully")
    
    # Verify the column exists
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_SCHEMA = %s 
        AND TABLE_NAME = 'clinics' 
        AND COLUMN_NAME = 'commercial_name'
    """, (MYSQL_DATABASE,))
    
    column_info = cursor.fetchone()
    
    if column_info:
        print("\n[Step 2] Verification:")
        print(f"  Column: {column_info[0]}")
        print(f"  Type: {column_info[1]}")
        print(f"  Nullable: {column_info[2]}")
        print(f"  Default: {column_info[3]}")
        print("\n✅ clinics table fixed successfully!")
    else:
        print("\n❌ ERROR: Column was not added properly")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ Fix Complete")
    print("=" * 70)
    print("\nThe clinics table now has the commercial_name column.")
    print("Login should work now. Please try again.")
    
except Error as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

