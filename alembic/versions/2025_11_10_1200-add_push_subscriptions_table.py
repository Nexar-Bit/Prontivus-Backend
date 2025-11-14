"""Add push_subscriptions table

Revision ID: add_push_subscriptions
Revises: d5c1472ec570
Create Date: 2025-11-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_push_subscriptions'
down_revision: Union[str, None] = 'd5c1472ec570'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create push_subscriptions table if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'push_subscriptions'
            ) THEN
                CREATE TABLE push_subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    endpoint VARCHAR(500) NOT NULL,
                    p256dh VARCHAR(200) NOT NULL,
                    auth VARCHAR(100) NOT NULL,
                    user_agent VARCHAR(500),
                    device_info JSONB,
                    is_active BOOLEAN NOT NULL DEFAULT true,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE
                );
                
                CREATE INDEX ix_push_subscriptions_user_id ON push_subscriptions(user_id);
                CREATE INDEX ix_push_subscriptions_endpoint ON push_subscriptions(endpoint);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index('ix_push_subscriptions_endpoint', table_name='push_subscriptions')
    op.drop_index('ix_push_subscriptions_user_id', table_name='push_subscriptions')
    op.drop_table('push_subscriptions')

