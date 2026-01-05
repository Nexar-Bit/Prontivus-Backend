"""Add document signatures table

Revision ID: add_document_signatures
Revises: add_menu_management
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_document_signatures'
down_revision: Union[str, None] = 'add_menu_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create document_signatures table
    op.create_table(
        'document_signatures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('crm_number', sa.String(length=20), nullable=False),
        sa.Column('crm_state', sa.String(length=2), nullable=False),
        sa.Column('certificate_serial', sa.String(length=255), nullable=True),
        sa.Column('certificate_issuer', sa.String(length=255), nullable=True),
        sa.Column('certificate_valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('certificate_valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('document_hash', sa.String(length=512), nullable=False),
        sa.Column('signature_data', sa.Text(), nullable=False),
        sa.Column('signature_algorithm', sa.String(length=50), nullable=False, server_default='RSA-SHA256'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='signed'),
        sa.Column('signed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['doctor_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_document_signatures_id', 'document_signatures', ['id'], unique=False)
    op.create_index('ix_document_signatures_document_type', 'document_signatures', ['document_type'], unique=False)
    op.create_index('ix_document_signatures_document_id', 'document_signatures', ['document_id'], unique=False)
    op.create_index('ix_document_signatures_doctor_id', 'document_signatures', ['doctor_id'], unique=False)
    op.create_index('ix_document_signatures_clinic_id', 'document_signatures', ['clinic_id'], unique=False)
    op.create_index('ix_document_signatures_status', 'document_signatures', ['status'], unique=False)
    op.create_index('ix_document_signatures_signed_at', 'document_signatures', ['signed_at'], unique=False)
    # Composite index for document lookup
    op.create_index('ix_document_signatures_doc_type_id', 'document_signatures', ['document_type', 'document_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_document_signatures_doc_type_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_signed_at', table_name='document_signatures')
    op.drop_index('ix_document_signatures_status', table_name='document_signatures')
    op.drop_index('ix_document_signatures_clinic_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_doctor_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_document_id', table_name='document_signatures')
    op.drop_index('ix_document_signatures_document_type', table_name='document_signatures')
    op.drop_index('ix_document_signatures_id', table_name='document_signatures')
    op.drop_table('document_signatures')
