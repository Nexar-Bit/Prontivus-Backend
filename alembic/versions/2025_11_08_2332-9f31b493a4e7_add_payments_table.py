"""add_payments_table

Revision ID: 9f31b493a4e7
Revises: add_tiss_templates
Create Date: 2025-11-08 23:32:54.901803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9f31b493a4e7'
down_revision: Union[str, None] = 'add_tiss_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create PaymentMethod enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentmethod AS ENUM (
                'cash', 'credit_card', 'debit_card', 'bank_transfer', 
                'pix', 'check', 'insurance', 'other'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create PaymentStatus enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE paymentstatus AS ENUM (
                'pending', 'completed', 'failed', 'cancelled', 'refunded'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Check if table already exists and create using raw SQL
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'payments'
            ) THEN
                -- Create payments table using raw SQL
                CREATE TABLE payments (
                    id SERIAL PRIMARY KEY,
                    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
                    amount NUMERIC(10, 2) NOT NULL,
                    method paymentmethod NOT NULL,
                    status paymentstatus NOT NULL DEFAULT 'pending',
                    paid_at TIMESTAMP WITH TIME ZONE,
                    reference_number VARCHAR(100),
                    notes TEXT,
                    created_by INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                
                CREATE INDEX ix_payments_id ON payments(id);
                CREATE INDEX ix_payments_invoice_id ON payments(invoice_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Drop table and indexes
    op.drop_index('ix_payments_invoice_id', table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS paymentmethod')
