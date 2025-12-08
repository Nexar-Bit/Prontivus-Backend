"""Add consultation_fee field to users (doctor default consultation price)

Revision ID: add_doctor_fee
Revises: add_doctor_consultation_room
Create Date: 2025-12-27 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_doctor_fee"
down_revision: Union[str, None] = "add_doctor_consultation_room"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add consultation_fee column to users table."""
    op.add_column(
        "users",
        sa.Column("consultation_fee", sa.Numeric(10, 2), nullable=True),
    )


def downgrade() -> None:
    """Remove consultation_fee column from users table."""
    op.drop_column("users", "consultation_fee")

