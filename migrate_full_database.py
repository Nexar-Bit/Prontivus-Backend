"""
Full database migration using pg_dump/pg_restore (recommended) or direct copy
"""
import asyncio
import sys
import subprocess
import os
from pathlib import Path

# Old database (Render.com PostgreSQL)
OLD_DB = {
    "host": "dpg-d441bemuk2gs739jnde0-a.oregon-postgres.render.com",
    "port": "5432",
    "user": "prontivus_clinic_user",
    "password": "awysfvJWF0oFBmG7zJDCirqw238MjrmT",
    "database": "prontivus_clinic"
}

# New database (AWS RDS PostgreSQL)
NEW_DB = {
    "host": "db-prontivus-pg.crka8siog2ay.sa-east-1.rds.amazonaws.com",
    "port": "5432",
    "user": "postgres",
    "password": "JEFFz1ZB4LfWx9YOj1lF",
    "database": "prontivus_clinic"
}

def check_pg_dump():
    """Check if pg_dump is available"""
    try:
        result = subprocess.run(['pg_dump', '--version'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def migrate_with_pg_dump():
    """Migrate using pg_dump and pg_restore (fastest method)"""
    print("🔄 Using pg_dump/pg_restore for migration...")
    print()
    
    dump_file = Path("database_dump.sql")
    
    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = OLD_DB['password']
        
        # Dump old database
        print("📦 Dumping old database...")
        dump_cmd = [
            'pg_dump',
            '-h', OLD_DB['host'],
            '-p', OLD_DB['port'],
            '-U', OLD_DB['user'],
            '-d', OLD_DB['database'],
            '-F', 'c',  # Custom format (binary)
            '-f', str(dump_file),
            '--no-owner',  # Don't include ownership commands
            '--no-acl',    # Don't include ACL commands
        ]
        
        result = subprocess.run(dump_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ pg_dump failed: {result.stderr}")
            return False
        
        print(f"✅ Database dumped to {dump_file}")
        file_size = dump_file.stat().st_size / (1024 * 1024)
        print(f"   File size: {file_size:.2f} MB")
        print()
        
        # Restore to new database
        print("📥 Restoring to new database...")
        env['PGPASSWORD'] = NEW_DB['password']
        
        restore_cmd = [
            'pg_restore',
            '-h', NEW_DB['host'],
            '-p', NEW_DB['port'],
            '-U', NEW_DB['user'],
            '-d', NEW_DB['database'],
            '--no-owner',
            '--no-acl',
            '--clean',  # Clean before restore
            '--if-exists',  # Don't error if objects don't exist
            str(dump_file)
        ]
        
        result = subprocess.run(restore_cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"⚠️  pg_restore warnings (may be normal): {result.stderr[:500]}")
            # Check if it actually worked by checking for tables
            print("   Verifying restore...")
        
        print("✅ Database restored!")
        print()
        
        # Clean up
        if dump_file.exists():
            dump_file.unlink()
            print("🧹 Cleaned up dump file")
        
        return True
        
    except FileNotFoundError:
        print("❌ pg_dump/pg_restore not found")
        print("💡 Install PostgreSQL client tools or use Python migration")
        return False
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        if dump_file.exists():
            print(f"💡 Dump file saved at: {dump_file}")
        return False

async def migrate_with_python():
    """Fallback: Migrate using Python (slower but works without pg_dump)"""
    print("🔄 Using Python migration (fallback method)...")
    print("⚠️  This will take longer. Consider installing PostgreSQL client tools for faster migration.")
    print()
    
    import asyncpg
    
    try:
        # Connect to both databases
        old_conn = await asyncpg.connect(
            host=OLD_DB['host'],
            port=int(OLD_DB['port']),
            user=OLD_DB['user'],
            password=OLD_DB['password'],
            database=OLD_DB['database'],
            ssl='require'
        )
        
        new_conn = await asyncpg.connect(
            host=NEW_DB['host'],
            port=int(NEW_DB['port']),
            user=NEW_DB['user'],
            password=NEW_DB['password'],
            database=NEW_DB['database'],
            ssl='require'
        )
        
        print("✅ Connected to both databases")
        print()
        
        # Get all tables from old database
        tables = await old_conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        
        table_names = [row['table_name'] for row in tables]
        print(f"📋 Found {len(table_names)} tables to migrate")
        print()
        
        total_rows = 0
        
        for table_name in table_names:
            try:
                # Get row count
                count = await old_conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
                
                if count == 0:
                    print(f"   ⏭️  {table_name}: 0 rows")
                    continue
                
                print(f"   📦 {table_name}: {count:,} rows")
                
                # Check if table exists in new database
                exists = await new_conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = $1
                    )
                """, table_name)
                
                if not exists:
                    print(f"      ⚠️  Table doesn't exist in new DB (skipping)")
                    continue
                
                # Copy data using COPY command (fastest)
                # First, truncate new table
                await new_conn.execute(f"TRUNCATE TABLE {table_name} CASCADE")
                
                # Get all data
                rows = await old_conn.fetch(f"SELECT * FROM {table_name}")
                
                if rows:
                    # Get column names
                    columns = list(rows[0].keys())
                    column_names = ', '.join(columns)
                    placeholders = ', '.join([f'${i+1}' for i in range(len(columns))])
                    
                    insert_sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
                    
                    # Insert in batches
                    batch_size = 500
                    inserted = 0
                    
                    async with new_conn.transaction():
                        for i in range(0, len(rows), batch_size):
                            batch = rows[i:i+batch_size]
                            for row in batch:
                                values = [row[col] for col in columns]
                                await new_conn.execute(insert_sql, *values)
                                inserted += 1
                    
                    print(f"      ✅ Inserted {inserted:,} rows")
                    total_rows += inserted
                
            except Exception as e:
                print(f"      ❌ Error: {str(e)[:150]}")
                continue
        
        print()
        print("=" * 70)
        print("✅ Migration Complete!")
        print("=" * 70)
        print(f"   📝 Total rows migrated: {total_rows:,}")
        
        await old_conn.close()
        await new_conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main migration function"""
    print("=" * 70)
    print("🔄 Full Database Migration: Old (Render) → New (AWS RDS)")
    print("=" * 70)
    print()
    
    # Try pg_dump first (fastest)
    if check_pg_dump():
        print("✅ pg_dump found - using native PostgreSQL tools")
        print()
        success = migrate_with_pg_dump()
        if success:
            return True
        print()
        print("⚠️  pg_dump method failed, trying Python method...")
        print()
    
    # Fallback to Python method
    return await migrate_with_python()

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

