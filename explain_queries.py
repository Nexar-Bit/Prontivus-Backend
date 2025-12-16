"""Use EXPLAIN to check if queries are using indexes"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import DATABASE_URL

async def explain_queries():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    queries = [
        ("Users by clinic", "SELECT COUNT(*) FROM users WHERE clinic_id = 1 AND is_active = 1"),
        ("Active patients", "SELECT COUNT(*) FROM patients WHERE clinic_id = 1 AND is_active = 1"),
        ("Appointments this month", """
            SELECT COUNT(*) FROM appointments 
            WHERE clinic_id = 1 
            AND scheduled_datetime >= DATE_SUB(NOW(), INTERVAL 1 MONTH)
        """),
    ]
    
    async with engine.connect() as conn:
        for name, query in queries:
            try:
                explain_query = f"EXPLAIN {query}"
                result = await conn.execute(text(explain_query))
                rows = result.fetchall()
                
                print(f"\n{name}:")
                print("-" * 70)
                print(f"Query: {query[:80]}...")
                print("\nEXPLAIN output:")
                for row in rows:
                    # Print key columns from EXPLAIN
                    print(f"  - type: {row[2] if len(row) > 2 else 'N/A'}, "
                          f"key: {row[4] if len(row) > 4 else 'N/A'}, "
                          f"rows: {row[8] if len(row) > 8 else 'N/A'}")
                
                # Check if index is being used
                if len(rows) > 0 and len(rows[0]) > 4:
                    key_used = rows[0][4]  # key column
                    if key_used:
                        print(f"  ✅ Using index: {key_used}")
                    else:
                        print(f"  ❌ No index used (full table scan)")
            except Exception as e:
                print(f"\n{name}: Error - {e}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(explain_queries())

