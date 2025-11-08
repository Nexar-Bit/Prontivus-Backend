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
    
    # Create payments table
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('method', sa.Enum('cash', 'credit_card', 'debit_card', 'bank_transfer', 'pix', 'check', 'insurance', 'other', name='paymentmethod'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'completed', 'failed', 'cancelled', 'refunded', name='paymentstatus'), nullable=False, server_default='pending'),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'], unique=False)


def downgrade() -> None:
    # Drop table and indexes
    op.drop_index('ix_payments_invoice_id', table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS paymentmethod')
