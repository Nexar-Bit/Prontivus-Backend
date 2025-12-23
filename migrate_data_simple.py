"""
Simple data migration using PostgreSQL COPY command
This is faster and more reliable for large datasets
"""
import asyncio
import sys
import asyncpg
from datetime import datetime

# Old database (Render.com PostgreSQL)
OLD_DB_CONFIG = {
    "host": "dpg-d441bemuk2gs739jnde0-a.oregon-postgres.render.com",
    "port": 5432,
    "user": "prontivus_clinic_user",
    "password": "awysfvJWF0oFBmG7zJDCirqw238MjrmT",
    "database": "prontivus_clinic",
    "ssl": "require"
}

# New database (AWS RDS PostgreSQL)
NEW_DB_CONFIG = {
    "host": "db-prontivus-pg.crka8siog2ay.sa-east-1.rds.amazonaws.com",
    "port": 5432,
    "user": "postgres",
    "password": "JEFFz1ZB4LfWx9YOj1lF",
    "database": "prontivus_clinic",
    "ssl": "require"
}

# Tables in dependency order
TABLES = [
    "user_roles",
    "clinics", 
    "users",
    "user_settings",
    "patients",
    "appointments",
    "clinical_records",
    "prescriptions",
    "exam_requests",
    "diagnoses",
    "licenses",
    "activations",
    "entitlements",
    "service_categories",
    "service_items",
    "invoices",
    "invoice_lines",
    "payments",
    "payment_methods",
    "insurance_plans",
    "preauth_requests",
    "expenses",
    "products",
    "product_categories",
    "stock_movements",
    "stock_alerts",
    "procedures",
    "procedure_products",
    "icd10_chapters",
    "icd10_groups",
    "icd10_categories",
    "icd10_subcategories",
    "icd10_search_index",
    "symptoms",
    "symptom_icd10_mappings",
    "voice_sessions",
    "voice_commands",
    "medical_terms",
    "voice_configurations",
    "patient_calls",
    "tiss_templates",
    "tiss_configs",
    "system_logs",
    "push_subscriptions",
    "message_threads",
    "messages",
    "menu_groups",
    "menu_items",
    "payment_method_configs",
    "report_configs",
    "tasks",
    "support_tickets",
    "help_articles",
    "password_reset_tokens",
    "file_uploads",
    "ai_configs",
    "migration_jobs",
]

async def get_table_count(conn, table_name):
    """Get row count for a table"""
    try:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
        return count
    except Exception:
        return 0

async def table_exists(conn, table_name):
    """Check if table exists"""
    try:
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = $1
            )
        """, table_name)
        return result
    except Exception:
        return False

async def migrate_table(old_conn, new_conn, table_name):
    """Migrate a single table"""
    try:
        # Check if table exists in both databases
        old_exists = await table_exists(old_conn, table_name)
        new_exists = await table_exists(new_conn, table_name)
        
        if not old_exists:
            print(f"   ⏭️  {table_name}: Not in old database (skipping)")
            return 0
        
        if not new_exists:
            print(f"   ⚠️  {table_name}: Not in new database (skipping - run migrations first)")
            return 0
        
        # Get row count
        old_count = await get_table_count(old_conn, table_name)
        
        if old_count == 0:
            print(f"   ⏭️  {table_name}: 0 rows (skipping)")
            return 0
        
        print(f"   📦 {table_name}: {old_count} rows")
        
        # Get all data
        rows = await old_conn.fetch(f"SELECT * FROM {table_name}")
        
        if not rows:
            return 0
        
        # Get column names
        columns = list(rows[0].keys())
        column_names = ', '.join(columns)
        placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
        
        # Insert data (using ON CONFLICT to handle duplicates)
        insert_sql = f"""
            INSERT INTO {table_name} ({column_names})
            VALUES ({placeholders})
            ON CONFLICT DO NOTHING
        """
        
        inserted = 0
        batch_size = 100
        
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i+batch_size]
            async with new_conn.transaction():
                for row in batch:
                    try:
                        values = [row[col] for col in columns]
                        result = await new_conn.execute(insert_sql, *values)
                        if 'INSERT' in result:
                            inserted += 1
                    except Exception as e:
                        # Skip duplicates and constraint violations
                        if "duplicate key" not in str(e).lower() and "unique constraint" not in str(e).lower():
                            print(f"      ⚠️  Error: {str(e)[:100]}")
        
        print(f"      ✅ Inserted {inserted}/{old_count} rows")
        return inserted
        
    except Exception as e:
        print(f"      ❌ Error: {str(e)[:200]}")
        return 0

async def main():
    """Main migration function"""
    print("=" * 70)
    print("🔄 Database Migration: Old (Render) → New (AWS RDS)")
    print("=" * 70)
    print()
    
    print("🔌 Connecting to databases...")
    
    try:
        old_conn = await asyncpg.connect(**OLD_DB_CONFIG)
        print("✅ Connected to OLD database (Render.com)")
        
        new_conn = await asyncpg.connect(**NEW_DB_CONFIG)
        print("✅ Connected to NEW database (AWS RDS)")
        print()
        
        # Check tables
        print("📋 Analyzing databases...")
        old_tables = await old_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        old_table_names = [row['table_name'] for row in old_tables]
        
        new_tables = await new_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        new_table_names = [row['table_name'] for row in new_tables]
        
        print(f"   Old database: {len(old_table_names)} tables")
        print(f"   New database: {len(new_table_names)} tables")
        print()
        
        if len(new_table_names) == 0:
            print("⚠️  New database has no tables!")
            print("💡 Run migrations first: alembic upgrade head")
            return False
        
        # Filter tables that exist in both
        tables_to_migrate = [t for t in TABLES if t in old_table_names and t in new_table_names]
        
        print(f"📦 Migrating {len(tables_to_migrate)} tables...")
        print()
        
        total_rows = 0
        successful_tables = 0
        
        for table_name in tables_to_migrate:
            rows = await migrate_table(old_conn, new_conn, table_name)
            total_rows += rows
            if rows > 0:
                successful_tables += 1
        
        print()
        print("=" * 70)
        print("✅ Migration Complete!")
        print("=" * 70)
        print(f"   📊 Tables migrated: {successful_tables}/{len(tables_to_migrate)}")
        print(f"   📝 Total rows migrated: {total_rows:,}")
        print()
        
        await old_conn.close()
        await new_conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

