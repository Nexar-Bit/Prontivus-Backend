"""add_payment_method_configs_table

Revision ID: 288e957cd946
Revises: add_menu_management
Create Date: 2025-11-15 03:01:32.654866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '288e957cd946'
down_revision: Union[str, None] = 'add_menu_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create payment_method_configs table
    op.create_table(
        'payment_method_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payment_method_configs_id'), 'payment_method_configs', ['id'], unique=False)
    op.create_index(op.f('ix_payment_method_configs_clinic_id'), 'payment_method_configs', ['clinic_id'], unique=False)
    op.create_unique_constraint('uq_payment_method_config_clinic_method', 'payment_method_configs', ['clinic_id', 'method'])


def downgrade() -> None:
    # Drop payment_method_configs table
    op.drop_constraint('uq_payment_method_config_clinic_method', 'payment_method_configs', type_='unique')
    op.drop_index(op.f('ix_payment_method_configs_clinic_id'), table_name='payment_method_configs')
    op.drop_index(op.f('ix_payment_method_configs_id'), table_name='payment_method_configs')
    op.drop_table('payment_method_configs')
