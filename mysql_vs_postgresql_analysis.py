"""
Analyze differences between MySQL and PostgreSQL that could cause 503 errors
"""
import asyncio
import time
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, event
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL

load_dotenv()

async def analyze_mysql_issues():
    """Analyze MySQL-specific issues"""
    print("=" * 70)
    print("MySQL vs PostgreSQL Analysis")
    print("=" * 70)
    
    print(f"\n📋 Current Configuration:")
    print(f"   Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    print(f"   Driver: aiomysql (async MySQL driver)")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=25,
        max_overflow=35,
        pool_timeout=2,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    # Track connection events
    connection_times = []
    
    @event.listens_for(engine.sync_engine, "connect")
    def receive_connect(dbapi_conn, connection_record):
        start = time.time()
        connection_times.append(("connect_start", start))
    
    @event.listens_for(engine.sync_engine, "checkout")
    def receive_checkout(dbapi_conn, connection_record, connection_proxy):
        start = time.time()
        connection_times.append(("checkout_start", start))
    
    print("\n1. Testing Connection Creation Time...")
    async with engine.connect() as conn:
        # Measure connection time
        start = time.time()
        await conn.execute(text("SELECT 1"))
        elapsed = (time.time() - start) * 1000
        print(f"   First connection + query: {elapsed:.2f}ms")
    
    print("\n2. Testing Connection Pool Behavior...")
    # Test multiple connections
    start = time.time()
    tasks = []
    for i in range(5):
        async def test_conn(conn_id):
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                return conn_id, result.scalar()
        
        tasks.append(test_conn(i))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = (time.time() - start) * 1000
    print(f"   5 concurrent connections: {total_time:.2f}ms")
    print(f"   Average per connection: {total_time/5:.2f}ms")
    
    print("\n3. Testing MySQL-Specific Issues...")
    async with engine.connect() as conn:
        # Check MySQL version
        result = await conn.execute(text("SELECT VERSION()"))
        version = result.scalar()
        print(f"   MySQL Version: {version}")
        
        # Check connection settings
        result = await conn.execute(text("SHOW VARIABLES LIKE 'wait_timeout'"))
        wait_timeout = result.fetchone()
        if wait_timeout:
            print(f"   wait_timeout: {wait_timeout[1]} seconds")
        
        result = await conn.execute(text("SHOW VARIABLES LIKE 'interactive_timeout'"))
        interactive_timeout = result.fetchone()
        if interactive_timeout:
            print(f"   interactive_timeout: {interactive_timeout[1]} seconds")
        
        # Check for connection issues
        result = await conn.execute(text("SHOW STATUS LIKE 'Threads_connected'"))
        threads_connected = result.fetchone()
        if threads_connected:
            print(f"   Current connections: {threads_connected[1]}")
        
        result = await conn.execute(text("SHOW STATUS LIKE 'Max_used_connections'"))
        max_used = result.fetchone()
        if max_used:
            print(f"   Max used connections: {max_used[1]}")
        
        # Check for connection errors
        result = await conn.execute(text("SHOW STATUS LIKE 'Connection_errors%'"))
        error_stats = result.fetchall()
        if error_stats:
            print(f"   Connection error stats:")
            for stat in error_stats:
                print(f"     {stat[0]}: {stat[1]}")
    
    print("\n4. Testing aiomysql Driver Performance...")
    # Test if aiomysql has overhead
    async with engine.connect() as conn:
        # Simple query
        start = time.time()
        await conn.execute(text("SELECT 1"))
        elapsed1 = (time.time() - start) * 1000
        
        # Query with result
        start = time.time()
        result = await conn.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        elapsed2 = (time.time() - start) * 1000
        
        print(f"   SELECT 1: {elapsed1:.2f}ms")
        print(f"   SELECT COUNT(*): {elapsed2:.2f}ms (found {count} users)")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("MySQL-Specific Issues Identified")
    print("=" * 70)
    
    print("\n🔍 Potential MySQL Issues:")
    print("1. **aiomysql Driver Overhead:**")
    print("   - aiomysql may have more overhead than asyncpg (PostgreSQL)")
    print("   - Connection creation might be slower")
    print("   - Query execution might have more overhead")
    
    print("\n2. **MySQL Connection Handling:**")
    print("   - MySQL connections may timeout faster")
    print("   - wait_timeout might be too short")
    print("   - Connection pool might not be recycling properly")
    
    print("\n3. **MySQL Query Performance:**")
    print("   - MySQL query optimizer might be slower")
    print("   - Index usage might be different")
    print("   - Query execution plan might be suboptimal")
    
    print("\n4. **Network/Connection Issues:**")
    print("   - If MySQL is remote, network latency adds up")
    print("   - Connection establishment might be slow")
    print("   - SSL/TLS handshake might add overhead")
    
    print("\n💡 Recommendations:")
    print("1. Check if MySQL is local or remote")
    print("2. Increase MySQL wait_timeout if connections are timing out")
    print("3. Consider using connection pooling at MySQL level")
    print("4. Check MySQL server resources (CPU, memory, disk)")
    print("5. Consider if aiomysql version is up to date")

if __name__ == "__main__":
    asyncio.run(analyze_mysql_issues())

