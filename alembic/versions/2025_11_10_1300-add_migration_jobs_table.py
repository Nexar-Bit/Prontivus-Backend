"""Add migration_jobs table

Revision ID: add_migration_jobs
Revises: add_push_subscriptions
Create Date: 2025-11-10 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_migration_jobs'
down_revision: Union[str, None] = 'add_push_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create MigrationType enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE migrationtype AS ENUM (
                'patients', 'appointments', 'clinical', 'financial'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create MigrationStatus enum
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE migrationstatus AS ENUM (
                'pending', 'running', 'completed', 'failed', 'rolled_back'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Create migration_jobs table
    op.create_table(
        'migration_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('patients', 'appointments', 'clinical', 'financial', name='migrationtype'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', 'rolled_back', name='migrationstatus'), nullable=False, server_default='pending'),
        sa.Column('input_format', sa.String(length=16), nullable=False),
        sa.Column('source_name', sa.String(length=255), nullable=True),
        sa.Column('params', sa.JSON(), nullable=True),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_migration_jobs_id', 'migration_jobs', ['id'], unique=False)
    op.create_index('ix_migration_jobs_clinic_id', 'migration_jobs', ['clinic_id'], unique=False)
    op.create_index('ix_migration_jobs_created_by', 'migration_jobs', ['created_by'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_migration_jobs_created_by', table_name='migration_jobs')
    op.drop_index('ix_migration_jobs_clinic_id', table_name='migration_jobs')
    op.drop_index('ix_migration_jobs_id', table_name='migration_jobs')
    op.drop_table('migration_jobs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS migrationstatus')
    op.execute('DROP TYPE IF EXISTS migrationtype')

