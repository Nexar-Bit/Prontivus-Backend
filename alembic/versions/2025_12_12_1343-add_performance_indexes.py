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
    from sqlalchemy import inspect, text
    conn = op.get_bind()
    
    def create_index_if_not_exists(table_name: str, index_name: str, columns: list):
        """Create index only if it doesn't exist"""
        try:
            # Check if index exists using raw SQL
            result = conn.execute(text(f"""
                SELECT COUNT(*) as count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
                AND table_name = '{table_name}'
                AND index_name = '{index_name}'
            """))
            exists = result.scalar() > 0
            
            if not exists:
                op.create_index(index_name, table_name, columns)
                print(f"Created index {index_name} on {table_name}")
            else:
                print(f"Index {index_name} on {table_name} already exists, skipping")
        except Exception as e:
            # If index creation fails, try to create it anyway (might be a different error)
            try:
                op.create_index(index_name, table_name, columns)
                print(f"Created index {index_name} on {table_name} (after error check)")
            except Exception as e2:
                print(f"Could not create index {index_name} on {table_name}: {e2}")
    
    # Users table indexes
    create_index_if_not_exists('users', 'idx_users_is_active', ['is_active'])
    
    # Patients table indexes
    create_index_if_not_exists('patients', 'idx_patients_is_active', ['is_active'])
    create_index_if_not_exists('patients', 'idx_patients_created_at', ['created_at'])
    
    # Clinical records table indexes
    # Note: clinical_records doesn't have clinic_id or patient_id directly
    # It has appointment_id which links to appointments (which have clinic_id and patient_id)
    create_index_if_not_exists('clinical_records', 'idx_clinical_records_created_at', ['created_at'])
    
    # Invoices table indexes
    # Note: invoices doesn't have clinic_id directly, but has appointment_id and patient_id
    create_index_if_not_exists('invoices', 'idx_invoices_issue_date', ['issue_date'])
    create_index_if_not_exists('invoices', 'idx_invoices_status', ['status'])
    
    # Payments table indexes
    create_index_if_not_exists('payments', 'idx_payments_payment_date', ['payment_date'])
    # Note: payments.status is JSON, cannot be indexed directly
    
    # Stock movements table indexes
    # Note: uses 'timestamp' not 'movement_date', and has clinic_id
    create_index_if_not_exists('stock_movements', 'idx_stock_movements_timestamp', ['timestamp'])
    create_index_if_not_exists('stock_movements', 'idx_stock_movements_clinic_id', ['clinic_id'])
    
    # Products table indexes
    create_index_if_not_exists('products', 'idx_products_is_active', ['is_active'])


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

