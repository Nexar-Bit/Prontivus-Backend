"""
Complete PostgreSQL to MySQL migration with proper dependency handling
Fixes foreign key constraints and schema mismatches
"""
import psycopg2
import mysql.connector
from mysql.connector import Error as MySQLError
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
import uuid

# PostgreSQL connection
PG_HOST = "dpg-d441bemuk2gs739jnde0-a.oregon-postgres.render.com"
PG_PORT = 5432
PG_DATABASE = "prontivus_clinic"
PG_USER = "prontivus_clinic_user"
PG_PASSWORD = "awysfvJWF0oFBmG7zJDCirqw238MjrmT"

# MySQL connection
MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

print("=" * 70)
print("Complete PostgreSQL to MySQL Migration (Fixed)")
print("=" * 70)

def convert_value(value, pg_type):
    """Convert PostgreSQL value to MySQL-compatible value"""
    if value is None:
        return None
    
    # UUID conversion
    if 'uuid' in pg_type.lower() or isinstance(value, uuid.UUID):
        return str(value)
    
    # Binary/bytea conversion
    if isinstance(value, (memoryview, bytes, bytearray)):
        return value.hex() if hasattr(value, 'hex') else bytes(value).hex()
    
    # JSON/JSONB conversion
    if 'json' in pg_type.lower():
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return value
    
    # Boolean conversion
    if pg_type == 'boolean':
        return bool(value)
    
    # Array conversion
    if '[]' in pg_type or 'array' in pg_type.lower():
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        return value
    
    # Enum conversion
    if 'enum' in pg_type.lower():
        return str(value)
    
    # Timestamp conversion
    if 'timestamp' in pg_type.lower():
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        return value
    
    return value

def fix_schema_mismatches(mysql_conn):
    """Fix schema mismatches between PostgreSQL and MySQL"""
    print("\n[FIX] Fixing schema mismatches...")
    cursor = mysql_conn.cursor()
    
    try:
        # Fix service_items - add clinic_id if missing
        cursor.execute("SHOW COLUMNS FROM service_items LIKE 'clinic_id'")
        if not cursor.fetchone():
            print("  Adding clinic_id to service_items...")
            cursor.execute("ALTER TABLE service_items ADD COLUMN clinic_id INT AFTER category")
            cursor.execute("UPDATE service_items SET clinic_id = 1 WHERE clinic_id IS NULL")
            cursor.execute("ALTER TABLE service_items MODIFY clinic_id INT NOT NULL")
            cursor.execute("ALTER TABLE service_items ADD FOREIGN KEY (clinic_id) REFERENCES clinics(id)")
            mysql_conn.commit()
            print("  OK: Fixed service_items")
    except Exception as e:
        print(f"  ERROR fixing service_items: {e}")
        mysql_conn.rollback()
    
    cursor.close()

def migrate_table_data(pg_conn, mysql_conn, table_name, clear_first=False):
    """Migrate data for a single table"""
    pg_cursor_dict = pg_conn.cursor(cursor_factory=RealDictCursor)
    pg_cursor = pg_conn.cursor()  # Regular cursor for column info
    mysql_cursor = mysql_conn.cursor()
    
    try:
        # Get row count
        pg_cursor_dict.execute(f'SELECT COUNT(*) as count FROM "{table_name}"')
        row_count = pg_cursor_dict.fetchone()['count']
        
        if row_count == 0:
            return True, 0, 0
        
        print(f"  Migrating {table_name} ({row_count} rows)...")
        
        # Clear table if requested
        if clear_first:
            mysql_cursor.execute(f"DELETE FROM `{table_name}`")
            mysql_conn.commit()
        
        # Get column information
        pg_cursor.execute("""
            SELECT 
                column_name,
                data_type,
                udt_name
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position
        """, (table_name,))
        columns_info = pg_cursor.fetchall()
        # columns_info is a list of tuples: (column_name, data_type, udt_name)
        column_names = [col[0] for col in columns_info]
        
        # Fetch all data
        try:
            pg_cursor_dict.execute(f'SELECT * FROM "{table_name}"')
            rows = pg_cursor_dict.fetchall()
        except Exception as e:
            print(f"    ERROR fetching data from PostgreSQL: {e}")
            return False, 0, 0
        
        # Check which columns exist in MySQL table
        mysql_cursor.execute(f"SHOW COLUMNS FROM `{table_name}`")
        mysql_columns = {row[0] for row in mysql_cursor.fetchall()}
        
        # Filter column_names to only include columns that exist in MySQL
        valid_columns = [col for col in column_names if col in mysql_columns]
        
        if not valid_columns:
            print(f"    WARN: No matching columns found for {table_name}")
            return False, 0, 0
        
        # Prepare insert statement with only valid columns
        placeholders = ', '.join(['%s'] * len(valid_columns))
        columns_str = ', '.join([f'`{col}`' for col in valid_columns])
        
        # Check if table has 'id' column for ON DUPLICATE KEY UPDATE
        if 'id' in mysql_columns:
            insert_sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE id=id"
        else:
            # For tables without id, use INSERT IGNORE
            insert_sql = f"INSERT IGNORE INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"
        
        # Migrate rows
        migrated = 0
        skipped = 0
        
        for row in rows:
            try:
                # Convert values - only for valid columns
                values = []
                for col_info in columns_info:
                    col_name = col_info[0]  # Tuple index 0
                    if col_name not in valid_columns:
                        continue
                    pg_type = col_info[1]    # Tuple index 1
                    value = row[col_name]
                    converted_value = convert_value(value, pg_type)
                    values.append(converted_value)
                
                # Insert into MySQL
                mysql_cursor.execute(insert_sql, values)
                migrated += 1
                
            except MySQLError as e:
                if e.errno == 1062:  # Duplicate entry
                    skipped += 1
                    continue
                elif e.errno == 1452:  # Foreign key constraint
                    skipped += 1
                    continue
                else:
                    print(f"    ERROR inserting row: {e}")
                    skipped += 1
                    continue
        
        mysql_conn.commit()
        
        print(f"    OK: Migrated {migrated} rows, skipped {skipped}")
        return True, migrated, skipped
        
    except Exception as e:
        print(f"    ERROR migrating {table_name}: {e}")
        import traceback
        traceback.print_exc()
        mysql_conn.rollback()
        return False, 0, 0
    finally:
        pg_cursor.close()
        pg_cursor_dict.close()
        mysql_cursor.close()

def main():
    # Migration order: tables without dependencies first
    migration_order = [
        # Level 1: No dependencies
        ['clinics', 'user_roles', 'icd10_chapters', 'icd10_groups', 'icd10_categories', 
         'icd10_subcategories', 'icd10_search_index', 'symptoms'],
        
        # Level 2: Depend on Level 1
        ['users', 'patients', 'licenses', 'medical_terms', 'symptom_icd10_mappings'],
        
        # Level 3: Depend on Level 2
        ['appointments', 'clinical_records', 'user_settings', 'exam_catalog', 
         'exam_requests', 'prescriptions', 'message_threads'],
        
        # Level 4: Depend on Level 3
        ['messages', 'clinical_record_versions', 'patient_calls', 'voice_sessions'],
        
        # Level 5: Financial (depend on clinics, users)
        ['service_items', 'invoices', 'invoice_lines', 'payments', 'payment_method_configs'],
        
        # Level 6: Stock (depend on clinics, products)
        ['products', 'stock_movements', 'stock_alerts'],
        
        # Level 7: Other
        ['ai_configs', 'report_configs', 'tiss_config', 'tiss_templates', 'expenses',
         'procedures', 'procedure_products', 'diagnoses', 'help_articles', 'tasks',
         'support_tickets', 'push_subscriptions', 'voice_commands', 'voice_configurations',
         'activations', 'entitlements', 'password_reset_tokens', 'migration_jobs'],
        
        # Level 8: Menu (already created)
        ['menu_groups', 'menu_items', 'role_menu_permissions'],
    ]
    
    try:
        # Connect to PostgreSQL
        print("\n[1/4] Connecting to PostgreSQL...")
        pg_conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            database=PG_DATABASE,
            user=PG_USER,
            password=PG_PASSWORD
        )
        print("  OK: Connected to PostgreSQL")
        
        # Connect to MySQL
        print("\n[2/4] Connecting to MySQL...")
        mysql_conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4'
        )
        print("  OK: Connected to MySQL")
        
        # Fix schema mismatches
        print("\n[3/4] Fixing schema mismatches...")
        fix_schema_mismatches(mysql_conn)
        
        # Migrate data in order
        print("\n[4/4] Migrating data...")
        print("=" * 70)
        
        total_migrated = 0
        total_skipped = 0
        total_failed = 0
        
        for level_idx, level_tables in enumerate(migration_order, 1):
            print(f"\nLevel {level_idx}: Migrating {len(level_tables)} tables...")
            
            for table_name in level_tables:
                success, migrated, skipped = migrate_table_data(
                    pg_conn, mysql_conn, table_name, clear_first=False
                )
                
                if success:
                    total_migrated += migrated
                    total_skipped += skipped
                else:
                    total_failed += 1
        
        print("\n" + "=" * 70)
        print("Migration Summary")
        print("=" * 70)
        print(f"Total rows migrated: {total_migrated}")
        print(f"Total rows skipped: {total_skipped}")
        print(f"Failed tables: {total_failed}")
        
        pg_conn.close()
        mysql_conn.close()
        
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()

