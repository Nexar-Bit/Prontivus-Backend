"""Add performance indexes for frequently queried columns

Revision ID: add_performance_indexes
Revises: add_doctor_fee
Create Date: 2025-12-12 13:43:00.000000

This migration adds indexes to improve query performance and reduce 503 errors
caused by slow database queries.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_performance_indexes"
down_revision: Union[str, None] = "2a41131b6481"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add indexes to improve query performance"""
    from sqlalchemy import text
    conn = op.get_bind()
    
    # Indexes to create (table_name, index_name, columns)
    # Note: Using correct column names from models
    indexes = [
        ('users', 'idx_users_is_active', ['is_active']),
        ('patients', 'idx_patients_is_active', ['is_active']),
        ('patients', 'idx_patients_created_at', ['created_at']),
        ('clinical_records', 'idx_clinical_records_created_at', ['created_at']),
        ('invoices', 'idx_invoices_issue_date', ['issue_date']),
        ('invoices', 'idx_invoices_status', ['status']),
        # Payments table uses 'paid_at', not 'payment_date'
        ('payments', 'idx_payments_paid_at', ['paid_at']),
        ('stock_movements', 'idx_stock_movements_timestamp', ['timestamp']),
        ('stock_movements', 'idx_stock_movements_clinic_id', ['clinic_id']),
        ('products', 'idx_products_is_active', ['is_active']),
    ]
    
    for table_name, index_name, columns in indexes:
        try:
            # Use CREATE INDEX IF NOT EXISTS with raw SQL (PostgreSQL 9.5+)
            columns_str = ', '.join(columns)
            conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {index_name} 
                ON {table_name} ({columns_str})
            """))
            print(f"Created index {index_name} on {table_name}")
        except Exception as e:
            # If table/column doesn't exist, skip silently
            print(f"Skipping index {index_name} on {table_name}: {e}")
            # Don't commit on error - let Alembic handle transaction
            continue


def downgrade() -> None:
    """Remove performance indexes"""
    
    # Drop indexes in reverse order
    try:
        op.drop_index('idx_products_is_active', table_name='products', if_exists=True)
        op.drop_index('idx_stock_movements_movement_date', table_name='stock_movements', if_exists=True)
        op.drop_index('idx_payments_status', table_name='payments', if_exists=True)
        op.drop_index('idx_payments_payment_date', table_name='payments', if_exists=True)
        op.drop_index('idx_invoices_status', table_name='invoices', if_exists=True)
        op.drop_index('idx_invoices_issue_date', table_name='invoices', if_exists=True)
        op.drop_index('idx_invoices_clinic_id', table_name='invoices', if_exists=True)
        op.drop_index('idx_clinical_records_created_at', table_name='clinical_records', if_exists=True)
        op.drop_index('idx_clinical_records_patient_id', table_name='clinical_records', if_exists=True)
        op.drop_index('idx_clinical_records_clinic_id', table_name='clinical_records', if_exists=True)
        op.drop_index('idx_patients_created_at', table_name='patients', if_exists=True)
        op.drop_index('idx_patients_is_active', table_name='patients', if_exists=True)
        op.drop_index('idx_users_is_active', table_name='users', if_exists=True)
    except Exception as e:
        print(f"Note: Some indexes may not exist: {e}")

