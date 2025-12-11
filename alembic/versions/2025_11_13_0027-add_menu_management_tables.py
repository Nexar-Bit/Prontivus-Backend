"""Add menu management tables and update user model

Revision ID: add_menu_management
Revises: add_migration_jobs
Create Date: 2025-11-13 00:27:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
# MySQL compatible - using JSON type directly

# revision identifiers, used by Alembic.
revision: str = 'add_menu_management'
down_revision: Union[str, None] = 'add_migration_jobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_user_roles_id', 'user_roles', ['id'], unique=False)
    op.create_index('ix_user_roles_name', 'user_roles', ['name'], unique=True)

    # Create menu_groups table
    op.create_table(
        'menu_groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_menu_groups_id', 'menu_groups', ['id'], unique=False)
    op.create_index('ix_menu_groups_name', 'menu_groups', ['name'], unique=False)
    op.create_index('ix_menu_groups_order_index', 'menu_groups', ['order_index'], unique=False)

    # Create menu_items table
    op.create_table(
        'menu_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('route', sa.String(length=200), nullable=False),
        sa.Column('icon', sa.String(length=50), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('permissions_required', sa.JSON, nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_external', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('badge', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['menu_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_menu_items_id', 'menu_items', ['id'], unique=False)
    op.create_index('ix_menu_items_group_id', 'menu_items', ['group_id'], unique=False)
    op.create_index('ix_menu_items_route', 'menu_items', ['route'], unique=False)
    op.create_index('ix_menu_items_order_index', 'menu_items', ['order_index'], unique=False)

    # Create role_menu_permissions association table
    op.create_table(
        'role_menu_permissions',
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('menu_item_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['user_roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['menu_item_id'], ['menu_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('role_id', 'menu_item_id')
    )

    # Add role_id and permissions columns to users table
    op.add_column('users', sa.Column('role_id', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('permissions', sa.JSON, nullable=True))
    op.create_index('ix_users_role_id', 'users', ['role_id'], unique=False)
    op.create_foreign_key('fk_users_role_id', 'users', 'user_roles', ['role_id'], ['id'])


def downgrade() -> None:
    # Remove foreign key and columns from users table
    op.drop_constraint('fk_users_role_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_role_id', table_name='users')
    op.drop_column('users', 'permissions')
    op.drop_column('users', 'role_id')

    # Drop association table
    op.drop_table('role_menu_permissions')

    # Drop menu_items table
    op.drop_index('ix_menu_items_order_index', table_name='menu_items')
    op.drop_index('ix_menu_items_route', table_name='menu_items')
    op.drop_index('ix_menu_items_group_id', table_name='menu_items')
    op.drop_index('ix_menu_items_id', table_name='menu_items')
    op.drop_table('menu_items')

    # Drop menu_groups table
    op.drop_index('ix_menu_groups_order_index', table_name='menu_groups')
    op.drop_index('ix_menu_groups_name', table_name='menu_groups')
    op.drop_index('ix_menu_groups_id', table_name='menu_groups')
    op.drop_table('menu_groups')

    # Drop user_roles table
    op.drop_index('ix_user_roles_name', table_name='user_roles')
    op.drop_index('ix_user_roles_id', table_name='user_roles')
    op.drop_table('user_roles')

