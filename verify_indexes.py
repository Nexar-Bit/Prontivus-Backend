"""Quick script to verify performance indexes were created"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from database import DATABASE_URL

async def verify_indexes():
    engine = create_async_engine(DATABASE_URL, echo=False)
    
    indexes_to_check = [
        ('users', 'idx_users_is_active'),
        ('patients', 'idx_patients_is_active'),
        ('patients', 'idx_patients_created_at'),
        ('clinical_records', 'idx_clinical_records_created_at'),
        ('invoices', 'idx_invoices_issue_date'),
        ('invoices', 'idx_invoices_status'),
        ('payments', 'idx_payments_payment_date'),
        ('stock_movements', 'idx_stock_movements_timestamp'),
        ('stock_movements', 'idx_stock_movements_clinic_id'),
        ('products', 'idx_products_is_active'),
    ]
    
    print("=" * 70)
    print("Verifying Performance Indexes")
    print("=" * 70)
    
    async with engine.connect() as conn:
        created_count = 0
        missing_count = 0
        
        for table_name, index_name in indexes_to_check:
            try:
                result = await conn.execute(text(f"""
                    SELECT COUNT(*) as count
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                    AND table_name = '{table_name}'
                    AND index_name = '{index_name}'
                """))
                exists = result.scalar() > 0
                
                if exists:
                    print(f"✅ {table_name}.{index_name}")
                    created_count += 1
                else:
                    print(f"❌ {table_name}.{index_name} - MISSING")
                    missing_count += 1
            except Exception as e:
                print(f"⚠️  {table_name}.{index_name} - Error checking: {e}")
                missing_count += 1
        
        print("\n" + "=" * 70)
        print(f"Summary: {created_count} indexes created, {missing_count} missing")
        print("=" * 70)
        
        if missing_count == 0:
            print("\n✅ All performance indexes are in place!")
        else:
            print(f"\n⚠️  {missing_count} indexes are missing. Check migration logs.")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(verify_indexes())

