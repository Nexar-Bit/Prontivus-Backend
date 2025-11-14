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
    
    # Create migration_jobs table if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'migration_jobs'
            ) THEN
                CREATE TABLE migration_jobs (
                    id SERIAL PRIMARY KEY,
                    clinic_id INTEGER NOT NULL,
                    created_by INTEGER NOT NULL,
                    type migrationtype NOT NULL,
                    status migrationstatus NOT NULL DEFAULT 'pending',
                    input_format VARCHAR(16) NOT NULL,
                    source_name VARCHAR(255),
                    params JSONB,
                    stats JSONB,
                    errors JSONB,
                    started_at TIMESTAMP WITH TIME ZONE,
                    completed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
                );
                
                CREATE INDEX ix_migration_jobs_id ON migration_jobs(id);
                CREATE INDEX ix_migration_jobs_clinic_id ON migration_jobs(clinic_id);
                CREATE INDEX ix_migration_jobs_created_by ON migration_jobs(created_by);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index('ix_migration_jobs_created_by', table_name='migration_jobs')
    op.drop_index('ix_migration_jobs_clinic_id', table_name='migration_jobs')
    op.drop_index('ix_migration_jobs_id', table_name='migration_jobs')
    op.drop_table('migration_jobs')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS migrationstatus')
    op.execute('DROP TYPE IF EXISTS migrationtype')

