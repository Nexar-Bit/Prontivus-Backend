"""
Check what tables exist in the database
"""
import asyncio
from sqlalchemy import text
from database import engine

async def check_tables():
    async with engine.connect() as conn:
        result = await conn.execute(text("SHOW TABLES"))
        tables = [row[0] for row in result]
        print(f"Existing tables ({len(tables)}):")
        for table in sorted(tables):
            print(f"  - {table}")
        return tables

if __name__ == "__main__":
    asyncio.run(check_tables())

