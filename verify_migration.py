"""
Verify data migration was successful
"""
import asyncio
import asyncpg
from datetime import datetime

# Database connections
OLD_DB = {
    "host": "dpg-d441bemuk2gs739jnde0-a.oregon-postgres.render.com",
    "port": 5432,
    "user": "prontivus_clinic_user",
    "password": "awysfvJWF0oFBmG7zJDCirqw238MjrmT",
    "database": "prontivus_clinic",
    "ssl": "require"
}

NEW_DB = {
    "host": "db-prontivus-pg.crka8siog2ay.sa-east-1.rds.amazonaws.com",
    "port": 5432,
    "user": "postgres",
    "password": "JEFFz1ZB4LfWx9YOj1lF",
    "database": "prontivus_clinic",
    "ssl": "require"
}

async def verify_migration():
    """Verify data was migrated correctly"""
    print("=" * 70)
    print("🔍 Verifying Database Migration")
    print("=" * 70)
    print()
    
    try:
        old_conn = await asyncpg.connect(**OLD_DB)
        new_conn = await asyncpg.connect(**NEW_DB)
        
        print("✅ Connected to both databases")
        print()
        
        # Get table counts
        tables = await old_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        print("📊 Comparing table row counts:")
        print()
        
        mismatches = []
        total_old = 0
        total_new = 0
        
        for table_row in tables:
            table_name = table_row['table_name']
            
            old_count = await old_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            new_count = await new_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            
            total_old += old_count
            total_new += new_count
            
            if old_count != new_count:
                mismatches.append((table_name, old_count, new_count))
                print(f"   ⚠️  {table_name}: Old={old_count:,} | New={new_count:,} ❌")
            elif old_count > 0:
                print(f"   ✅ {table_name}: {old_count:,} rows")
        
        print()
        print("=" * 70)
        print("📈 Summary")
        print("=" * 70)
        print(f"   📋 Tables checked: {len(tables)}")
        print(f"   📝 Total rows (old): {total_old:,}")
        print(f"   📝 Total rows (new): {total_new:,}")
        
        if mismatches:
            print(f"   ⚠️  Mismatches: {len(mismatches)} tables")
            for table, old, new in mismatches:
                print(f"      • {table}: {old} → {new}")
        else:
            print("   ✅ All tables match!")
        
        # Check key tables
        print()
        print("🔑 Key Tables Verification:")
        key_tables = ['users', 'clinics', 'patients', 'appointments', 'invoices']
        for table in key_tables:
            try:
                old_count = await old_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                new_count = await new_conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                status = "✅" if old_count == new_count else "❌"
                print(f"   {status} {table}: {old_count} → {new_count}")
            except:
                print(f"   ⚠️  {table}: Table not found")
        
        await old_conn.close()
        await new_conn.close()
        
        return len(mismatches) == 0
        
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_migration())
    exit(0 if success else 1)

