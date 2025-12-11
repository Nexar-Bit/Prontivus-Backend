"""
Script to set up MySQL database for Prontivus
This script creates the database if it doesn't exist and tests the connection.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# MySQL connection details
MYSQL_HOST = "db-prontivus.crka8siog2ay.sa-east-1.rds.amazonaws.com"
MYSQL_USER = "admin"
MYSQL_PASSWORD = "cMgoIYsgrGYlTt23LVVq"
MYSQL_DATABASE = "prontivus_clinic"

# Connection URL without database (to create it if needed)
BASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/"

# Connection URL with database
DATABASE_URL = f"mysql+aiomysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}"


async def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    print(f"Connecting to MySQL server at {MYSQL_HOST}...")
    
    # Connect without specifying database
    engine = create_async_engine(
        BASE_URL,
        echo=False,
        connect_args={
            "charset": "utf8mb4",
        },
    )
    
    try:
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{MYSQL_DATABASE}'")
            )
            exists = result.fetchone()
            
            if not exists:
                print(f"Database '{MYSQL_DATABASE}' does not exist. Creating...")
                # Create database with UTF8MB4 charset
                await conn.execute(text(f"CREATE DATABASE `{MYSQL_DATABASE}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                await conn.commit()
                print(f"✓ Database '{MYSQL_DATABASE}' created successfully!")
            else:
                print(f"✓ Database '{MYSQL_DATABASE}' already exists.")
            
    except Exception as e:
        print(f"✗ Error creating database: {e}")
        raise
    finally:
        await engine.dispose()


async def test_connection():
    """Test connection to the database"""
    print(f"\nTesting connection to database '{MYSQL_DATABASE}'...")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    try:
        async with engine.connect() as conn:
            # Test query
            result = await conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"✓ Successfully connected to MySQL!")
            print(f"  MySQL Version: {version}")
            
            # Check charset
            result = await conn.execute(text("SELECT @@character_set_database, @@collation_database"))
            charset, collation = result.fetchone()
            print(f"  Database Charset: {charset}")
            print(f"  Database Collation: {collation}")
            
    except Exception as e:
        print(f"✗ Error connecting to database: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Main function"""
    print("=" * 60)
    print("Prontivus MySQL Database Setup")
    print("=" * 60)
    
    try:
        # Create database if it doesn't exist
        await create_database_if_not_exists()
        
        # Test connection
        await test_connection()
        
        print("\n" + "=" * 60)
        print("✓ Setup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Set DATABASE_URL environment variable:")
        print(f"   DATABASE_URL={DATABASE_URL}")
        print("2. Run migrations:")
        print("   alembic upgrade head")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

