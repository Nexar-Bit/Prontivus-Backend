"""Check actual column names in database tables"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import DATABASE_URL

async def check_columns():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    tables_to_check = [
        'clinical_records',
        'invoices',
        'payments',
        'stock_movements',
    ]
    
    async with engine.connect() as conn:
        for table in tables_to_check:
            try:
                result = await conn.execute(text(f"DESCRIBE {table}"))
                columns = result.fetchall()
                print(f"\n{table}:")
                print("-" * 50)
                for col in columns:
                    print(f"  {col[0]} ({col[1]})")
            except Exception as e:
                print(f"\n{table}: Error - {e}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_columns())

