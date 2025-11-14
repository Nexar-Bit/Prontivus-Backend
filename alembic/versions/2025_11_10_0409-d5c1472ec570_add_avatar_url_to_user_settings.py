"""add_avatar_url_to_user_settings

Revision ID: d5c1472ec570
Revises: 9f31b493a4e7
Create Date: 2025-11-10 04:09:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5c1472ec570'
down_revision: Union[str, Sequence[str], None] = ('003_add_voice_models', '004_add_patient_calling', '9f31b493a4e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add avatar_url column to user_settings table if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'user_settings' 
                AND column_name = 'avatar_url'
            ) THEN
                ALTER TABLE user_settings ADD COLUMN avatar_url VARCHAR(500);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove avatar_url column from user_settings table
    op.drop_column('user_settings', 'avatar_url')

