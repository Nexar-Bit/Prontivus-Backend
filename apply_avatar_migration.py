#!/usr/bin/env python3
"""
Direct migration script to add avatar_url column
Use this if alembic migration has issues with multiple heads
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

async def apply_migration():
    """Apply avatar_url column migration directly"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            # Check if column exists
            check_query = text("""
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'user_settings' 
                AND column_name = 'avatar_url'
            """)
            
            result = await conn.execute(check_query)
            exists = result.scalar_one_or_none()
            
            if exists:
                print("✅ Column 'avatar_url' already exists in 'user_settings' table")
            else:
                # Add column
                alter_query = text("""
                    ALTER TABLE user_settings 
                    ADD COLUMN avatar_url VARCHAR(500)
                """)
                await conn.execute(alter_query)
                print("✅ Column 'avatar_url' added successfully to 'user_settings' table")
        
        print("\n✅ Migration completed successfully!")
        print("   You can now use the avatar upload feature.")
        
    except Exception as e:
        print(f"❌ Error applying migration: {e}")
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(apply_migration())

