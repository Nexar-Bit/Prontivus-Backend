"""Add TISS templates table

Revision ID: add_tiss_templates
Revises: 2a77b43d4b6f
Create Date: 2025-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tiss_templates'
down_revision: Union[str, None] = '2a77b43d4b6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tisstemplatecategory AS ENUM (
                'consultation', 'procedure', 'exam', 'emergency', 'custom'
            );
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)
    
    # Check if table already exists
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tiss_templates'
            ) THEN
                -- Create tiss_templates table using raw SQL
                CREATE TABLE tiss_templates (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    category tisstemplatecategory NOT NULL,
                    xml_template TEXT NOT NULL,
                    variables JSONB,
                    is_default BOOLEAN NOT NULL DEFAULT false,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                    created_by_id INTEGER REFERENCES users(id),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX ix_tiss_templates_id ON tiss_templates(id);
                CREATE INDEX ix_tiss_templates_name ON tiss_templates(name);
                CREATE INDEX ix_tiss_templates_clinic_id ON tiss_templates(clinic_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index(op.f('ix_tiss_templates_clinic_id'), table_name='tiss_templates')
    op.drop_index(op.f('ix_tiss_templates_name'), table_name='tiss_templates')
    op.drop_index(op.f('ix_tiss_templates_id'), table_name='tiss_templates')
    op.drop_table('tiss_templates')
    op.execute("DROP TYPE IF EXISTS tisstemplatecategory")

