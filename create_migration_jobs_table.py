"""
Direct script to create migration_jobs table
Use this if Alembic migrations are in an inconsistent state
"""
import asyncio
from database import get_async_session
from sqlalchemy import text


async def create_migration_jobs_table():
    """Create migration_jobs table and required enums"""
    async for db in get_async_session():
        try:
            # Create MigrationType enum
            await db.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE migrationtype AS ENUM (
                        'patients', 'appointments', 'clinical', 'financial'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Create MigrationStatus enum
            await db.execute(text("""
                DO $$ BEGIN
                    CREATE TYPE migrationstatus AS ENUM (
                        'pending', 'running', 'completed', 'failed', 'rolled_back'
                    );
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """))
            
            # Check if table exists
            result = await db.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'migration_jobs'
                );
            """))
            table_exists = result.scalar()
            
            if not table_exists:
                # Create migration_jobs table
                await db.execute(text("""
                    CREATE TABLE migration_jobs (
                        id SERIAL PRIMARY KEY,
                        clinic_id INTEGER NOT NULL,
                        created_by INTEGER NOT NULL,
                        type migrationtype NOT NULL,
                        status migrationstatus NOT NULL DEFAULT 'pending',
                        input_format VARCHAR(16) NOT NULL,
                        source_name VARCHAR(255),
                        params JSONB,
                        stats JSONB,
                        errors JSONB,
                        started_at TIMESTAMP WITH TIME ZONE,
                        completed_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                    );
                """))
                
                # Create indexes
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_migration_jobs_id ON migration_jobs(id);
                """))
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_migration_jobs_clinic_id ON migration_jobs(clinic_id);
                """))
                await db.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_migration_jobs_created_by ON migration_jobs(created_by);
                """))
                
                await db.commit()
                print("✅ migration_jobs table created successfully!")
            else:
                print("ℹ️  migration_jobs table already exists")
            
            break
        except Exception as e:
            await db.rollback()
            print(f"❌ Error creating migration_jobs table: {e}")
            import traceback
            traceback.print_exc()
            break


if __name__ == "__main__":
    asyncio.run(create_migration_jobs_table())

