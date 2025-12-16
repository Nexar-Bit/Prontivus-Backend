"""
Test raw SQL performance to see if it's ORM or database issue
"""
import asyncio
import time
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL, POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT

load_dotenv()

async def test_raw_sql():
    """Test raw SQL queries to see if database itself is slow"""
    print("=" * 70)
    print("Raw SQL Performance Test")
    print("=" * 70)
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    print("\n1. Testing simple SELECT 1...")
    async with engine.connect() as conn:
        start = time.time()
        try:
            result = await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=2.0
            )
            elapsed = (time.time() - start) * 1000
            print(f"   ✅ SELECT 1: {elapsed:.2f}ms")
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ SELECT 1: Timeout after {elapsed:.2f}ms")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ SELECT 1: Error - {e} ({elapsed:.2f}ms)")
    
    print("\n2. Testing user lookup by primary key (raw SQL)...")
    async with engine.connect() as conn:
        start = time.time()
        try:
            result = await asyncio.wait_for(
                conn.execute(text("SELECT id, email, username FROM users WHERE id = 1 LIMIT 1")),
                timeout=2.0
            )
            row = result.fetchone()
            elapsed = (time.time() - start) * 1000
            if row:
                print(f"   ✅ User lookup: {elapsed:.2f}ms - Found user {row[1]}")
            else:
                print(f"   ⚠️  User lookup: {elapsed:.2f}ms - No user found")
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ User lookup: Timeout after {elapsed:.2f}ms")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ User lookup: Error - {e} ({elapsed:.2f}ms)")
    
    print("\n3. Testing user lookup with JOIN (raw SQL)...")
    async with engine.connect() as conn:
        start = time.time()
        try:
            result = await asyncio.wait_for(
                conn.execute(text("""
                    SELECT u.id, u.email, u.username, c.name as clinic_name 
                    FROM users u 
                    LEFT JOIN clinics c ON u.clinic_id = c.id 
                    WHERE u.id = 1 
                    LIMIT 1
                """)),
                timeout=2.0
            )
            row = result.fetchone()
            elapsed = (time.time() - start) * 1000
            if row:
                print(f"   ✅ User+Clinic lookup: {elapsed:.2f}ms - Found user {row[1]}")
            else:
                print(f"   ⚠️  User+Clinic lookup: {elapsed:.2f}ms - No user found")
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ User+Clinic lookup: Timeout after {elapsed:.2f}ms")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ User+Clinic lookup: Error - {e} ({elapsed:.2f}ms)")
    
    print("\n4. Testing EXPLAIN on user query...")
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("EXPLAIN SELECT * FROM users WHERE id = 1"))
            rows = result.fetchall()
            print("   EXPLAIN output:")
            for row in rows:
                # Print key columns
                if len(row) > 4:
                    key_used = row[4] if row[4] else "None"
                    print(f"     - Key used: {key_used}")
                    print(f"     - Type: {row[2] if len(row) > 2 else 'N/A'}")
        except Exception as e:
            print(f"   ❌ Error running EXPLAIN: {e}")
    
    print("\n5. Checking database server status...")
    async with engine.connect() as conn:
        try:
            # Check process list
            result = await conn.execute(text("SHOW PROCESSLIST"))
            processes = result.fetchall()
            print(f"   Current MySQL processes: {len(processes)}")
            
            # Check for slow queries
            long_running = [p for p in processes if len(p) > 5 and p[5] and p[5] > 1]
            if long_running:
                print(f"   ⚠️  Found {len(long_running)} long-running queries (>1 second)")
                for p in long_running[:5]:  # Show first 5
                    print(f"     - Query: {p[7][:50] if len(p) > 7 and p[7] else 'N/A'}...")
            else:
                print(f"   ✅ No long-running queries detected")
        except Exception as e:
            print(f"   ⚠️  Could not check process list: {e}")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("Diagnosis")
    print("=" * 70)
    print("If raw SQL is also slow (>500ms), the issue is:")
    print("  1. Database server performance (CPU, memory, disk I/O)")
    print("  2. Network latency to database server")
    print("  3. MySQL configuration issues")
    print("  4. Database server is overloaded or on slow hardware")
    print("\nIf raw SQL is fast but ORM is slow, the issue is:")
    print("  1. ORM overhead")
    print("  2. selectinload causing extra queries")
    print("  3. SQLAlchemy connection issues")

if __name__ == "__main__":
    asyncio.run(test_raw_sql())

