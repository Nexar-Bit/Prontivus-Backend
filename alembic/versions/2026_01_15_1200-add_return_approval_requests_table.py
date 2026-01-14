"""add_return_approval_requests_table

Revision ID: add_return_approval_requests
Revises: 1d8b34150b42
Create Date: 2026-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_return_approval_requests'
down_revision: Union[str, None] = '1d8b34150b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ReturnApprovalStatus enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'returnapprovalstatus') THEN
                CREATE TYPE returnapprovalstatus AS ENUM ('pending', 'approved', 'rejected', 'expired');
            END IF;
        END $$;
    """)
    
    # Create return_approval_requests table
    op.create_table(
        'return_approval_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('requested_appointment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('appointment_type', sa.String(length=100), nullable=False, server_default='retorno'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('returns_count_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', 'expired', name='returnapprovalstatus'), nullable=False, server_default='pending'),
        sa.Column('requested_by', sa.Integer(), nullable=False),
        sa.Column('approved_by', sa.Integer(), nullable=True),
        sa.Column('approval_notes', sa.Text(), nullable=True),
        sa.Column('resulting_appointment_id', sa.Integer(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
        sa.ForeignKeyConstraint(['requested_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['resulting_appointment_id'], ['appointments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_return_approval_requests_id'), 'return_approval_requests', ['id'], unique=False)
    op.create_index(op.f('ix_return_approval_requests_patient_id'), 'return_approval_requests', ['patient_id'], unique=False)
    op.create_index(op.f('ix_return_approval_requests_doctor_id'), 'return_approval_requests', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_return_approval_requests_clinic_id'), 'return_approval_requests', ['clinic_id'], unique=False)
    op.create_index(op.f('ix_return_approval_requests_status'), 'return_approval_requests', ['status'], unique=False)
    op.create_index(op.f('ix_return_approval_requests_resulting_appointment_id'), 'return_approval_requests', ['resulting_appointment_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_return_approval_requests_resulting_appointment_id'), table_name='return_approval_requests')
    op.drop_index(op.f('ix_return_approval_requests_status'), table_name='return_approval_requests')
    op.drop_index(op.f('ix_return_approval_requests_clinic_id'), table_name='return_approval_requests')
    op.drop_index(op.f('ix_return_approval_requests_doctor_id'), table_name='return_approval_requests')
    op.drop_index(op.f('ix_return_approval_requests_patient_id'), table_name='return_approval_requests')
    op.drop_index(op.f('ix_return_approval_requests_id'), table_name='return_approval_requests')
    op.drop_table('return_approval_requests')
    
    # Drop enum
    op.execute("DROP TYPE IF EXISTS returnapprovalstatus")
