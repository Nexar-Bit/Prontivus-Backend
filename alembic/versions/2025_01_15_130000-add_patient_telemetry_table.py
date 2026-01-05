"""Add patient telemetry table

Revision ID: add_patient_telemetry
Revises: add_document_signatures
Create Date: 2025-01-15 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_patient_telemetry'
down_revision: Union[str, None] = 'add_document_signatures'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create patient_telemetry table
    op.create_table(
        'patient_telemetry',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('measured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('systolic_bp', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('diastolic_bp', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('heart_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('temperature', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('oxygen_saturation', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('respiratory_rate', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('weight', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('height', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('bmi', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('steps', sa.Integer(), nullable=True),
        sa.Column('calories_burned', sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column('activity_minutes', sa.Integer(), nullable=True),
        sa.Column('sleep_hours', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('sleep_quality', sa.String(length=20), nullable=True),
        sa.Column('blood_glucose', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('additional_metrics', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('recorded_by', sa.Integer(), nullable=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_patient_telemetry_id', 'patient_telemetry', ['id'], unique=False)
    op.create_index('ix_patient_telemetry_patient_id', 'patient_telemetry', ['patient_id'], unique=False)
    op.create_index('ix_patient_telemetry_clinic_id', 'patient_telemetry', ['clinic_id'], unique=False)
    op.create_index('ix_patient_telemetry_measured_at', 'patient_telemetry', ['measured_at'], unique=False)
    op.create_index('ix_patient_telemetry_created_at', 'patient_telemetry', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_patient_telemetry_created_at', table_name='patient_telemetry')
    op.drop_index('ix_patient_telemetry_measured_at', table_name='patient_telemetry')
    op.drop_index('ix_patient_telemetry_clinic_id', table_name='patient_telemetry')
    op.drop_index('ix_patient_telemetry_patient_id', table_name='patient_telemetry')
    op.drop_index('ix_patient_telemetry_id', table_name='patient_telemetry')
    op.drop_table('patient_telemetry')
