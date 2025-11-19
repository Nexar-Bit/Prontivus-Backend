"""change_task_priority_to_varchar

Revision ID: 28d428fcbfe1
Revises: 9b28f911c2db
Create Date: 2025-11-19 08:58:20.886980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28d428fcbfe1'
down_revision: Union[str, None] = '9b28f911c2db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # First, remove the default value that depends on the enum type
    op.execute("""
        ALTER TABLE tasks 
        ALTER COLUMN priority DROP DEFAULT
    """)
    
    # Alter the priority column from ENUM to VARCHAR
    # Convert existing enum values to strings
    op.execute("""
        ALTER TABLE tasks 
        ALTER COLUMN priority TYPE VARCHAR(50) 
        USING priority::text
    """)
    
    # Set the new default value as a string
    op.execute("""
        ALTER TABLE tasks 
        ALTER COLUMN priority SET DEFAULT 'Média'
    """)
    
    # Drop the enum type if it exists (only if not used elsewhere)
    # Check if enum is used in other tables
    connection = op.get_bind()
    result = connection.execute(sa.text("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE udt_name = 'taskpriority'
    """)).scalar()
    
    if result == 0:
        # No other columns use this enum, safe to drop
        op.execute("DROP TYPE IF EXISTS taskpriority")


def downgrade() -> None:
    # Recreate the enum type
    op.execute("""
        CREATE TYPE taskpriority AS ENUM ('Baixa', 'Média', 'Alta')
    """)
    
    # Convert the column back to ENUM
    op.execute("""
        ALTER TABLE tasks 
        ALTER COLUMN priority TYPE taskpriority 
        USING priority::taskpriority
    """)
