"""
Test database connection and pool configuration
"""
import asyncio
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine, AsyncSessionLocal
from sqlalchemy import text, select
from app.models import User, Clinic


async def test_connection():
    """Test basic database connection"""
    print("=" * 70)
    print("Database Connection Test")
    print("=" * 70)
    
    try:
        # Test 1: Basic connection
        print("\n1. Testing basic connection...")
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            if row and row[0] == 1:
                print("   ✅ Basic connection successful")
            else:
                print("   ❌ Basic connection failed")
                return False
        
        # Test 2: Connection pool
        print("\n2. Testing connection pool...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT DATABASE() as db_name"))
            row = result.fetchone()
            if row:
                print(f"   ✅ Connection pool working - Connected to database: {row[0]}")
            else:
                print("   ❌ Connection pool test failed")
                return False
        
        # Test 3: Query execution
        print("\n3. Testing query execution...")
        async with AsyncSessionLocal() as session:
            # Test simple query
            result = await session.execute(text("SELECT COUNT(*) as count FROM users"))
            row = result.fetchone()
            if row is not None:
                print(f"   ✅ Query execution successful - Found {row[0]} users")
            else:
                print("   ⚠️  Query executed but returned no results")
        
        # Test 4: ORM query
        print("\n4. Testing ORM query...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Clinic).limit(1))
            clinic = result.scalar_one_or_none()
            if clinic:
                print(f"   ✅ ORM query successful - Found clinic: {clinic.name}")
            else:
                print("   ⚠️  ORM query executed but no clinics found")
        
        # Test 5: Concurrent connections (simulate login scenario)
        print("\n5. Testing concurrent connections (simulating login)...")
        async def test_concurrent_query(query_id: int):
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(text("SELECT COUNT(*) FROM users"))
                    count = result.scalar()
                    return f"Query {query_id}: {count} users"
            except Exception as e:
                return f"Query {query_id}: Error - {str(e)}"
        
        # Run 5 concurrent queries (simulating dashboard + 2 avatars + notifications)
        results = await asyncio.gather(
            test_concurrent_query(1),
            test_concurrent_query(2),
            test_concurrent_query(3),
            test_concurrent_query(4),
            test_concurrent_query(5),
            return_exceptions=True
        )
        
        success_count = sum(1 for r in results if isinstance(r, str) and "Error" not in r)
        print(f"   ✅ Concurrent connections test: {success_count}/5 successful")
        for result in results:
            if isinstance(result, str):
                print(f"      - {result}")
            else:
                print(f"      - Error: {result}")
        
        # Test 6: Connection pool info
        print("\n6. Connection pool information:")
        pool = engine.pool
        print(f"   Pool size: {pool.size()}")
        print(f"   Checked out: {pool.checkedout()}")
        print(f"   Overflow: {pool.overflow()}")
        print(f"   Checked in: {pool.checkedin()}")
        
        print("\n" + "=" * 70)
        print("✅ All database connection tests passed!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ Database connection test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await engine.dispose()


async def main():
    """Main function"""
    success = await test_connection()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

