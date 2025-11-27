"""add symptom tables

Revision ID: add_symptom_tables
Revises: 0444c1bfb215
Create Date: 2025-12-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_symptom_tables'
down_revision: Union[str, None] = '0444c1bfb215'  # After ai_config migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create symptoms table
    op.create_table('symptoms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('name_normalized', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_symptoms_id'), 'symptoms', ['id'], unique=False)
    op.create_index('ix_symptoms_name', 'symptoms', ['name'], unique=True)
    op.create_index('ix_symptoms_name_normalized', 'symptoms', ['name_normalized'], unique=False)
    op.create_index('ix_symptoms_category', 'symptoms', ['category'], unique=False)
    
    # Create symptom_icd10_mappings table
    op.create_table('symptom_icd10_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symptom_id', sa.Integer(), nullable=False),
        sa.Column('icd10_code', sa.String(length=10), nullable=False),
        sa.Column('relevance_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['symptom_id'], ['symptoms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_symptom_icd10_mappings_id'), 'symptom_icd10_mappings', ['id'], unique=False)
    op.create_index('ix_symptom_icd10_symptom', 'symptom_icd10_mappings', ['symptom_id'], unique=False)
    op.create_index('ix_symptom_icd10_code', 'symptom_icd10_mappings', ['icd10_code'], unique=False)
    op.create_index('ix_symptom_icd10_relevance', 'symptom_icd10_mappings', ['relevance_score'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_symptom_icd10_relevance', table_name='symptom_icd10_mappings')
    op.drop_index('ix_symptom_icd10_code', table_name='symptom_icd10_mappings')
    op.drop_index('ix_symptom_icd10_symptom', table_name='symptom_icd10_mappings')
    op.drop_index(op.f('ix_symptom_icd10_mappings_id'), table_name='symptom_icd10_mappings')
    op.drop_table('symptom_icd10_mappings')
    
    op.drop_index('ix_symptoms_category', table_name='symptoms')
    op.drop_index('ix_symptoms_name_normalized', table_name='symptoms')
    op.drop_index('ix_symptoms_name', table_name='symptoms')
    op.drop_index(op.f('ix_symptoms_id'), table_name='symptoms')
    op.drop_table('symptoms')

