"""add_report_configs_table

Revision ID: dbd8b3e4aa07
Revises: 288e957cd946
Create Date: 2025-11-15 03:05:56.306148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dbd8b3e4aa07'
down_revision: Union[str, None] = '288e957cd946'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create report_configs table
    op.create_table(
        'report_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('financial', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('clinical', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('operational', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('general', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_report_configs_id'), 'report_configs', ['id'], unique=False)
    op.create_index(op.f('ix_report_configs_clinic_id'), 'report_configs', ['clinic_id'], unique=True)
    op.create_unique_constraint('uq_report_config_clinic', 'report_configs', ['clinic_id'])


def downgrade() -> None:
    # Drop report_configs table
    op.drop_constraint('uq_report_config_clinic', 'report_configs', type_='unique')
    op.drop_index(op.f('ix_report_configs_clinic_id'), table_name='report_configs')
    op.drop_index(op.f('ix_report_configs_id'), table_name='report_configs')
    op.drop_table('report_configs')
