"""
Verify that the connection pool size increase is working
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL, POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT

load_dotenv()

async def verify_pool_configuration():
    """Verify the pool configuration is correct"""
    print("=" * 70)
    print("Connection Pool Configuration Verification")
    print("=" * 70)
    
    print(f"\n📋 Expected Configuration:")
    print(f"   Pool Size: {POOL_SIZE}")
    print(f"   Max Overflow: {MAX_OVERFLOW}")
    print(f"   Total Max Connections: {POOL_SIZE + MAX_OVERFLOW}")
    print(f"   Pool Timeout: {POOL_TIMEOUT}s")
    
    # Create engine with current settings
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=3600,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    print(f"\n✅ Engine Created with Configuration:")
    print(f"   Pool Size: {engine.pool.size()}")
    print(f"   Max Overflow: {engine.pool._max_overflow}")
    print(f"   Pool Timeout: {engine.pool._timeout}s")
    
    # Check MySQL max_connections
    print(f"\n🔍 Checking MySQL Server Configuration...")
    async with engine.connect() as conn:
        # Check MySQL max_connections
        result = await conn.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
        max_conn_row = result.fetchone()
        if max_conn_row:
            mysql_max_conn = int(max_conn_row[1])
            print(f"   MySQL max_connections: {mysql_max_conn}")
            if mysql_max_conn < (POOL_SIZE + MAX_OVERFLOW):
                print(f"   ⚠️  WARNING: MySQL max_connections ({mysql_max_conn}) is less than pool max ({POOL_SIZE + MAX_OVERFLOW})")
                print(f"   This could cause connection failures!")
            else:
                print(f"   ✅ MySQL max_connections is sufficient")
        
        # Check current connections
        result = await conn.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
        threads_row = result.fetchone()
        if threads_row:
            current_connections = int(threads_row[1])
            print(f"   Current MySQL connections: {current_connections}")
        
        # Check max used connections
        result = await conn.execute(text("SHOW STATUS LIKE 'Max_used_connections'"))
        max_used_row = result.fetchone()
        if max_used_row:
            max_used = int(max_used_row[1])
            print(f"   Max used connections (ever): {max_used}")
    
    # Test pool behavior
    print(f"\n🧪 Testing Pool Behavior...")
    
    # Get initial pool state
    print(f"   Initial pool state:")
    print(f"     Size: {engine.pool.size()}")
    print(f"     Checked out: {engine.pool.checkedout()}")
    print(f"     Overflow: {engine.pool.overflow()}")
    print(f"     Checked in: {engine.pool.checkedin()}")
    
    # Test concurrent connections
    print(f"\n   Testing concurrent connections...")
    async def test_connection(conn_id: int):
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            await asyncio.sleep(0.1)  # Simulate query time
            return conn_id
    
    # Try to create multiple connections concurrently
    num_test_connections = min(10, POOL_SIZE + 5)  # Test with 10 or pool_size + 5
    tasks = [test_connection(i) for i in range(num_test_connections)]
    
    try:
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=5.0
        )
        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = len(results) - successful
        print(f"     Tested {num_test_connections} concurrent connections:")
        print(f"       Successful: {successful}")
        print(f"       Failed: {failed}")
        
        if failed > 0:
            print(f"     ⚠️  Some connections failed - check pool configuration")
        else:
            print(f"     ✅ All connections successful")
    except asyncio.TimeoutError:
        print(f"     ❌ Connection test timed out - pool may be exhausted")
    
    # Final pool state
    print(f"\n   Final pool state:")
    print(f"     Size: {engine.pool.size()}")
    print(f"     Checked out: {engine.pool.checkedout()}")
    print(f"     Overflow: {engine.pool.overflow()}")
    print(f"     Checked in: {engine.pool.checkedin()}")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("Verification Complete")
    print("=" * 70)
    
    # Recommendations
    print("\n💡 Recommendations:")
    if mysql_max_conn and mysql_max_conn < (POOL_SIZE + MAX_OVERFLOW):
        print("   1. Increase MySQL max_connections to at least 70")
        print("      Edit MySQL config or run: SET GLOBAL max_connections = 100;")
    print("   2. Monitor pool usage in production")
    print("   3. If pool exhaustion persists, consider:")
    print("      - Further query optimization")
    print("      - Increasing pool size more")
    print("      - Database server optimization")

if __name__ == "__main__":
    asyncio.run(verify_pool_configuration())

