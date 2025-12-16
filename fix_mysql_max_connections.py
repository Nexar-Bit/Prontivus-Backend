"""
Fix MySQL max_connections to match pool size
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import DATABASE_URL, POOL_SIZE, MAX_OVERFLOW

load_dotenv()

async def fix_max_connections():
    """Increase MySQL max_connections to match pool size"""
    print("=" * 70)
    print("MySQL max_connections Fix")
    print("=" * 70)
    
    required_connections = POOL_SIZE + MAX_OVERFLOW
    recommended_connections = max(100, required_connections + 20)  # Add buffer
    
    print(f"\n📋 Current Configuration:")
    print(f"   Pool Size: {POOL_SIZE}")
    print(f"   Max Overflow: {MAX_OVERFLOW}")
    print(f"   Required MySQL connections: {required_connections}")
    print(f"   Recommended MySQL connections: {recommended_connections}")
    
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        connect_args={
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION'",
        },
    )
    
    async with engine.connect() as conn:
        # Check current max_connections
        result = await conn.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
        max_conn_row = result.fetchone()
        current_max = int(max_conn_row[1]) if max_conn_row else 0
        
        print(f"\n🔍 Current MySQL Configuration:")
        print(f"   max_connections: {current_max}")
        
        if current_max < required_connections:
            print(f"\n⚠️  PROBLEM DETECTED:")
            print(f"   MySQL max_connections ({current_max}) is less than pool max ({required_connections})")
            print(f"   This will cause connection failures when pool tries to use all connections!")
            
            print(f"\n🔧 Attempting to fix...")
            try:
                # Try to set max_connections (requires SUPER privilege)
                await conn.execute(text(f"SET GLOBAL max_connections = {recommended_connections}"))
                await conn.commit()
                
                # Verify it was set
                result = await conn.execute(text("SHOW VARIABLES LIKE 'max_connections'"))
                new_max_row = result.fetchone()
                new_max = int(new_max_row[1]) if new_max_row else 0
                
                if new_max >= required_connections:
                    print(f"   ✅ Successfully set max_connections to {new_max}")
                    print(f"   ✅ Pool can now use up to {required_connections} connections")
                else:
                    print(f"   ⚠️  Set to {new_max}, but still less than required {required_connections}")
                    print(f"   You may need SUPER privilege or edit MySQL config file")
            except Exception as e:
                print(f"   ❌ Failed to set max_connections: {e}")
                print(f"\n   Manual Fix Required:")
                print(f"   1. Connect to MySQL as root/SuperAdmin")
                print(f"   2. Run: SET GLOBAL max_connections = {recommended_connections};")
                print(f"   3. Or edit MySQL config file (my.cnf or my.ini):")
                print(f"      [mysqld]")
                print(f"      max_connections = {recommended_connections}")
                print(f"   4. Restart MySQL server")
        else:
            print(f"\n✅ MySQL max_connections ({current_max}) is sufficient")
            print(f"   Pool can use up to {required_connections} connections")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("Fix Complete")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(fix_max_connections())

