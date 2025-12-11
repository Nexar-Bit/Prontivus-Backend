"""merge_exam_catalog_and_doctor_fee

Revision ID: 2a41131b6481
Revises: add_exam_catalog, add_doctor_fee
Create Date: 2025-12-10 23:21:33.111286

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2a41131b6481'
down_revision: Union[str, None] = ('add_exam_catalog', 'add_doctor_fee')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
