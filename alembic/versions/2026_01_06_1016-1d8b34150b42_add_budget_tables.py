"""add_budget_tables

Revision ID: 1d8b34150b42
Revises: 
Create Date: 2026-01-06 10:16:03.963562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1d8b34150b42'
down_revision: Union[str, None] = 'add_tiss_complete'  # Latest migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if tables already exist
    from sqlalchemy import inspect
    from sqlalchemy.dialects.postgresql import ENUM
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create BudgetStatus enum if it doesn't exist
    # Use native PostgreSQL approach to avoid SQLAlchemy automatic creation
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'budgetstatus') THEN
                CREATE TYPE budgetstatus AS ENUM ('draft', 'sent', 'accepted', 'rejected', 'converted', 'expired');
            END IF;
        END $$;
    """)
    
    # Create budgets table
    if 'budgets' not in existing_tables:
        # Create the enum type object pointing to existing type
        budgetstatus_enum = ENUM('draft', 'sent', 'accepted', 'rejected', 'converted', 'expired', 
                                   name='budgetstatus', create_type=False)
        
        op.create_table('budgets',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('patient_id', sa.Integer(), nullable=False),
            sa.Column('appointment_id', sa.Integer(), nullable=True),
            sa.Column('clinic_id', sa.Integer(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('issue_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('status', budgetstatus_enum, nullable=False),
            sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('converted_to_invoice_id', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
            sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ),
            sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
            sa.ForeignKeyConstraint(['converted_to_invoice_id'], ['invoices.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_budgets_id'), 'budgets', ['id'], unique=False)
        op.create_index('ix_budgets_patient_id', 'budgets', ['patient_id'], unique=False)
        op.create_index('ix_budgets_appointment_id', 'budgets', ['appointment_id'], unique=False)
        op.create_index('ix_budgets_clinic_id', 'budgets', ['clinic_id'], unique=False)
        op.create_index('ix_budgets_status', 'budgets', ['status'], unique=False)
    
    # Create budget_lines table
    if 'budget_lines' not in existing_tables:
        op.create_table('budget_lines',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('budget_id', sa.Integer(), nullable=False),
            sa.Column('service_item_id', sa.Integer(), nullable=True),
            sa.Column('procedure_id', sa.Integer(), nullable=True),
            sa.Column('quantity', sa.Numeric(precision=8, scale=2), nullable=False),
            sa.Column('unit_price', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('line_total', sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column('description', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
            sa.ForeignKeyConstraint(['budget_id'], ['budgets.id'], ),
            sa.ForeignKeyConstraint(['service_item_id'], ['service_items.id'], ),
            sa.ForeignKeyConstraint(['procedure_id'], ['procedures.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_budget_lines_id'), 'budget_lines', ['id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_budget_lines_id'), table_name='budget_lines')
    op.drop_table('budget_lines')
    op.drop_index('ix_budgets_status', table_name='budgets')
    op.drop_index('ix_budgets_clinic_id', table_name='budgets')
    op.drop_index('ix_budgets_appointment_id', table_name='budgets')
    op.drop_index('ix_budgets_patient_id', table_name='budgets')
    op.drop_index(op.f('ix_budgets_id'), table_name='budgets')
    op.drop_table('budgets')
    
    # Drop enum
    op.execute('DROP TYPE IF EXISTS budgetstatus')
