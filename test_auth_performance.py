"""
Test auth endpoint performance to identify bottlenecks
"""
import asyncio
import time
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL, POOL_SIZE, MAX_OVERFLOW, POOL_TIMEOUT
from app.models import User

load_dotenv()

async def test_user_lookup_performance():
    """Test how fast user lookup queries are"""
    print("=" * 70)
    print("User Lookup Performance Test")
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
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Test 1: Simple user lookup (no clinic)
    print("\n1. Testing simple user lookup (no clinic relationship)...")
    async with async_session() as session:
        start = time.time()
        try:
            result = await asyncio.wait_for(
                session.execute(select(User).where(User.id == 1)),
                timeout=2.0
            )
            user = result.scalar_one_or_none()
            elapsed = (time.time() - start) * 1000
            if user:
                print(f"   ✅ Found user: {user.email} ({elapsed:.2f}ms)")
            else:
                print(f"   ⚠️  User not found ({elapsed:.2f}ms)")
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ Timeout after {elapsed:.2f}ms")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ Error: {e} ({elapsed:.2f}ms)")
    
    # Test 2: User lookup with clinic (selectinload)
    print("\n2. Testing user lookup with clinic (selectinload)...")
    async with async_session() as session:
        start = time.time()
        try:
            query = select(User).options(selectinload(User.clinic)).where(User.id == 1)
            result = await asyncio.wait_for(
                session.execute(query),
                timeout=2.0
            )
            user = result.scalar_one_or_none()
            elapsed = (time.time() - start) * 1000
            if user:
                clinic_name = user.clinic.name if user.clinic else "None"
                print(f"   ✅ Found user: {user.email}, clinic: {clinic_name} ({elapsed:.2f}ms)")
            else:
                print(f"   ⚠️  User not found ({elapsed:.2f}ms)")
        except asyncio.TimeoutError:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ Timeout after {elapsed:.2f}ms")
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"   ❌ Error: {e} ({elapsed:.2f}ms)")
    
    # Test 3: Concurrent user lookups (simulating real load)
    print("\n3. Testing concurrent user lookups (simulating real load)...")
    async def lookup_user(user_id: int):
        async with async_session() as session:
            start = time.time()
            try:
                query = select(User).options(selectinload(User.clinic)).where(User.id == user_id)
                result = await asyncio.wait_for(
                    session.execute(query),
                    timeout=2.0
                )
                user = result.scalar_one_or_none()
                elapsed = (time.time() - start) * 1000
                return user_id, elapsed, user is not None, None
            except asyncio.TimeoutError:
                elapsed = (time.time() - start) * 1000
                return user_id, elapsed, False, "timeout"
            except Exception as e:
                elapsed = (time.time() - start) * 1000
                return user_id, elapsed, False, str(e)
    
    # Test with multiple concurrent lookups
    user_ids = [1, 2, 3, 4, 5]  # Test with first 5 users
    tasks = [lookup_user(uid) for uid in user_ids]
    
    start = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = (time.time() - start) * 1000
    
    successful = 0
    timeouts = 0
    errors = 0
    total_elapsed = 0
    
    for result in results:
        if isinstance(result, Exception):
            errors += 1
            print(f"   ❌ Exception: {result}")
        else:
            user_id, elapsed, success, error = result
            total_elapsed += elapsed
            if error == "timeout":
                timeouts += 1
                print(f"   ❌ User {user_id}: Timeout ({elapsed:.2f}ms)")
            elif error:
                errors += 1
                print(f"   ❌ User {user_id}: Error - {error} ({elapsed:.2f}ms)")
            elif success:
                successful += 1
                print(f"   ✅ User {user_id}: Success ({elapsed:.2f}ms)")
            else:
                errors += 1
                print(f"   ⚠️  User {user_id}: Not found ({elapsed:.2f}ms)")
    
    avg_time = total_elapsed / len(results) if results else 0
    print(f"\n   Summary:")
    print(f"     Successful: {successful}/{len(user_ids)}")
    print(f"     Timeouts: {timeouts}")
    print(f"     Errors: {errors}")
    print(f"     Average time: {avg_time:.2f}ms")
    print(f"     Total time: {total_time:.2f}ms")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("Performance Test Complete")
    print("=" * 70)
    
    if avg_time > 500:
        print("\n⚠️  WARNING: Average query time is >500ms")
        print("   This is very slow and will cause pool exhaustion under load")
        print("   Recommendations:")
        print("   1. Check database server performance")
        print("   2. Verify indexes are being used (run EXPLAIN)")
        print("   3. Consider database server optimization")
    elif avg_time > 200:
        print("\n⚠️  WARNING: Average query time is >200ms")
        print("   This is slow and may cause issues under heavy load")
    else:
        print("\n✅ Query performance is acceptable")

if __name__ == "__main__":
    asyncio.run(test_user_lookup_performance())

