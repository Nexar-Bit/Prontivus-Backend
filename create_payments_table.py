"""
Script to create the payments table directly in the database
Run this if the migration fails
"""
import asyncio
from sqlalchemy import text
from database import engine

async def create_payments_table():
    """Create the payments table and enums"""
    async with engine.begin() as conn:
        # Create PaymentMethod enum if it doesn't exist
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE paymentmethod AS ENUM (
                    'cash', 'credit_card', 'debit_card', 'bank_transfer', 
                    'pix', 'check', 'insurance', 'other'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create PaymentStatus enum if it doesn't exist
        await conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE paymentstatus AS ENUM (
                    'pending', 'completed', 'failed', 'cancelled', 'refunded'
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        
        # Create payments table if it doesn't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                invoice_id INTEGER NOT NULL REFERENCES invoices(id),
                amount NUMERIC(10, 2) NOT NULL,
                method paymentmethod NOT NULL,
                status paymentstatus NOT NULL DEFAULT 'pending',
                paid_at TIMESTAMP WITH TIME ZONE,
                reference_number VARCHAR(100),
                notes TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """))
        
        # Create indexes (one at a time)
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_id ON payments(id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_payments_invoice_id ON payments(invoice_id)"))
        
        print("✅ Payments table created successfully!")

if __name__ == "__main__":
    asyncio.run(create_payments_table())

