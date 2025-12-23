"""
Migrate all data from old database to new database
"""
import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text, inspect
from sqlalchemy.orm import selectinload
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Old database (Render.com PostgreSQL)
OLD_DATABASE_URL = "postgresql+asyncpg://prontivus_clinic_user:awysfvJWF0oFBmG7zJDCirqw238MjrmT@dpg-d441bemuk2gs739jnde0-a.oregon-postgres.render.com/prontivus_clinic"

# New database (AWS RDS PostgreSQL)
NEW_DATABASE_URL = os.getenv("DATABASE_URL", "")

if not NEW_DATABASE_URL:
    print("❌ NEW_DATABASE_URL not found in .env file")
    sys.exit(1)

# Table order for migration (respecting foreign key dependencies)
TABLE_ORDER = [
    # Core tables first (no dependencies)
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

async def get_tables(engine):
    """Get list of tables from database"""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """))
        return [row[0] for row in result.fetchall()]

async def get_table_count(engine, table_name):
    """Get row count for a table"""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar()
    except Exception as e:
        return 0

async def migrate_table(old_engine, new_engine, table_name):
    """Migrate a single table"""
    try:
        # Get row count from old database
        old_count = await get_table_count(old_engine, table_name)
        
        if old_count == 0:
            print(f"   ⏭️  {table_name}: 0 rows (skipping)")
            return 0
        
        print(f"   📦 {table_name}: {old_count} rows")
        
        # Get all data from old database
        async with old_engine.connect() as old_conn:
            result = await old_conn.execute(text(f"SELECT * FROM {table_name}"))
            rows = result.fetchall()
            columns = result.keys()
        
        if not rows:
            return 0
        
        # Insert into new database
        async with new_engine.begin() as new_conn:
            # Disable foreign key checks temporarily (PostgreSQL doesn't support this directly)
            # We'll handle it by migrating in the correct order
            
            # Build INSERT statement
            column_names = ', '.join(columns)
            placeholders = ', '.join([f':{col}' for col in columns])
            
            insert_sql = f"""
                INSERT INTO {table_name} ({column_names})
                VALUES ({placeholders})
                ON CONFLICT DO NOTHING
            """
            
            inserted = 0
            for row in rows:
                try:
                    row_dict = dict(zip(columns, row))
                    await new_conn.execute(text(insert_sql), row_dict)
                    inserted += 1
                except Exception as e:
                    # Skip duplicate or constraint violations
                    if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
                        continue
                    print(f"      ⚠️  Error inserting row: {str(e)[:100]}")
            
            print(f"      ✅ Inserted {inserted}/{old_count} rows")
            return inserted
            
    except Exception as e:
        print(f"      ❌ Error migrating {table_name}: {str(e)[:200]}")
        return 0

async def main():
    """Main migration function"""
    print("=" * 70)
    print("🔄 Database Migration: Old → New")
    print("=" * 70)
    print()
    
    # Create engines
    print("🔌 Connecting to databases...")
    old_engine = create_async_engine(
        OLD_DATABASE_URL,
        connect_args={"ssl": "require"},
        echo=False
    )
    
    new_engine = create_async_engine(
        NEW_DATABASE_URL,
        connect_args={"ssl": "require"},
        echo=False
    )
    
    try:
        # Test connections
        async with old_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Connected to OLD database (Render.com)")
        
        async with new_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Connected to NEW database (AWS RDS)")
        print()
        
        # Get tables from both databases
        print("📋 Analyzing databases...")
        old_tables = await get_tables(old_engine)
        new_tables = await get_tables(new_engine)
        
        print(f"   Old database: {len(old_tables)} tables")
        print(f"   New database: {len(new_tables)} tables")
        print()
        
        if len(new_tables) == 0:
            print("⚠️  New database has no tables!")
            print("💡 Run migrations first: alembic upgrade head")
            return False
        
        # Check which tables exist in old database
        tables_to_migrate = [t for t in TABLE_ORDER if t in old_tables and t in new_tables]
        missing_in_new = [t for t in old_tables if t not in new_tables]
        missing_in_old = [t for t in new_tables if t not in old_tables]
        
        if missing_in_new:
            print(f"⚠️  Tables in old DB but not in new DB: {', '.join(missing_in_new)}")
            print("   These will be skipped. Run migrations to create them.")
            print()
        
        if missing_in_old:
            print(f"ℹ️  New tables (not in old DB): {', '.join(missing_in_old)}")
            print()
        
        print(f"📦 Migrating {len(tables_to_migrate)} tables...")
        print()
        
        total_rows = 0
        successful_tables = 0
        
        for table_name in tables_to_migrate:
            rows = await migrate_table(old_engine, new_engine, table_name)
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
        print("💡 Next steps:")
        print("   1. Verify data in new database")
        print("   2. Update application to use new database")
        print("   3. Test all functionality")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await old_engine.dispose()
        await new_engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

