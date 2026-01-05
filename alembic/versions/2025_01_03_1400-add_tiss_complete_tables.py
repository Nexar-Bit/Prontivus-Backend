"""Add complete TISS tables structure

Revision ID: add_tiss_complete
Revises: add_performance_indexes
Create Date: 2025-01-03 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'add_tiss_complete'
down_revision: Union[str, None] = ('add_patient_telemetry', 'add_performance_indexes')  # Merge both heads
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create TISS version table
    op.create_table(
        'tiss_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(20), nullable=False, unique=True),
        sa.Column('xsd_file_path', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('end_of_life_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version')
    )
    op.create_index('ix_tiss_versions_version', 'tiss_versions', ['version'], unique=True)
    
    # Create TUSS codes table
    op.create_table(
        'tiss_tuss_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(10), nullable=False),
        sa.Column('descricao', sa.String(500), nullable=False),
        sa.Column('tabela', sa.String(2), nullable=False),
        sa.Column('data_inicio_vigencia', sa.Date(), nullable=False),
        sa.Column('data_fim_vigencia', sa.Date(), nullable=True),
        sa.Column('versao_tuss', sa.String(20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_tuss_codes_codigo', 'tiss_tuss_codes', ['codigo'], unique=False)
    op.create_index('ix_tiss_tuss_codes_tabela', 'tiss_tuss_codes', ['tabela'], unique=False)
    op.create_index('ix_tiss_tuss_codes_codigo_tabela', 'tiss_tuss_codes', ['codigo', 'tabela'], unique=False)
    
    # Create TUSS version history
    op.create_table(
        'tiss_tuss_version_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tuss_code_id', sa.Integer(), nullable=False),
        sa.Column('versao_anterior', sa.String(20), nullable=True),
        sa.Column('versao_nova', sa.String(20), nullable=False),
        sa.Column('data_alteracao', sa.Date(), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tuss_code_id'], ['tiss_tuss_codes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_tuss_version_history_tuss_code_id', 'tiss_tuss_version_history', ['tuss_code_id'], unique=False)
    
    # Create Consultation Guides table
    op.create_table(
        'tiss_consultation_guides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('appointment_id', sa.Integer(), nullable=True),
        sa.Column('numero_guia', sa.String(20), nullable=False),
        sa.Column('tipo_guia', sa.String(1), nullable=False, server_default='1'),
        sa.Column('data_emissao', sa.Date(), nullable=False),
        sa.Column('prestador_data', sa.JSON(), nullable=False),
        sa.Column('operadora_data', sa.JSON(), nullable=False),
        sa.Column('beneficiario_data', sa.JSON(), nullable=False),
        sa.Column('contratado_data', sa.JSON(), nullable=False),
        sa.Column('procedimentos_data', sa.JSON(), nullable=True),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('hash_integridade', sa.String(64), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('versao_tiss', sa.String(20), nullable=False, server_default='3.05.02'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_consultation_guides_clinic_id', 'tiss_consultation_guides', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_consultation_guides_numero_guia', 'tiss_consultation_guides', ['numero_guia'], unique=False)
    op.create_index('ix_tiss_consultation_guides_status', 'tiss_consultation_guides', ['status'], unique=False)
    op.create_index('ix_tiss_consultation_guides_invoice_id', 'tiss_consultation_guides', ['invoice_id'], unique=False)
    
    # Create SP/SADT Guides table
    op.create_table(
        'tiss_sadt_guides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('appointment_id', sa.Integer(), nullable=True),
        sa.Column('numero_guia', sa.String(20), nullable=False),
        sa.Column('data_emissao', sa.Date(), nullable=False),
        sa.Column('prestador_data', sa.JSON(), nullable=False),
        sa.Column('operadora_data', sa.JSON(), nullable=False),
        sa.Column('beneficiario_data', sa.JSON(), nullable=False),
        sa.Column('contratado_data', sa.JSON(), nullable=False),
        sa.Column('sadt_data', sa.JSON(), nullable=False),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('hash_integridade', sa.String(64), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('versao_tiss', sa.String(20), nullable=False, server_default='3.05.02'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_sadt_guides_clinic_id', 'tiss_sadt_guides', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_sadt_guides_numero_guia', 'tiss_sadt_guides', ['numero_guia'], unique=False)
    op.create_index('ix_tiss_sadt_guides_status', 'tiss_sadt_guides', ['status'], unique=False)
    
    # Create Hospitalization Guides table
    op.create_table(
        'tiss_hospitalization_guides',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('appointment_id', sa.Integer(), nullable=True),
        sa.Column('numero_guia', sa.String(20), nullable=False),
        sa.Column('data_emissao', sa.Date(), nullable=False),
        sa.Column('prestador_data', sa.JSON(), nullable=False),
        sa.Column('operadora_data', sa.JSON(), nullable=False),
        sa.Column('beneficiario_data', sa.JSON(), nullable=False),
        sa.Column('contratado_data', sa.JSON(), nullable=False),
        sa.Column('internacao_data', sa.JSON(), nullable=False),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('hash_integridade', sa.String(64), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('versao_tiss', sa.String(20), nullable=False, server_default='3.05.02'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['appointment_id'], ['appointments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_hospitalization_guides_clinic_id', 'tiss_hospitalization_guides', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_hospitalization_guides_numero_guia', 'tiss_hospitalization_guides', ['numero_guia'], unique=False)
    op.create_index('ix_tiss_hospitalization_guides_status', 'tiss_hospitalization_guides', ['status'], unique=False)
    
    # Create Individual Fees table
    op.create_table(
        'tiss_individual_fees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=True),
        sa.Column('numero_guia', sa.String(20), nullable=False),
        sa.Column('data_emissao', sa.Date(), nullable=False),
        sa.Column('prestador_data', sa.JSON(), nullable=False),
        sa.Column('operadora_data', sa.JSON(), nullable=False),
        sa.Column('beneficiario_data', sa.JSON(), nullable=False),
        sa.Column('profissional_data', sa.JSON(), nullable=False),
        sa.Column('honorario_data', sa.JSON(), nullable=False),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('hash_integridade', sa.String(64), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('versao_tiss', sa.String(20), nullable=False, server_default='3.05.02'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_individual_fees_clinic_id', 'tiss_individual_fees', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_individual_fees_numero_guia', 'tiss_individual_fees', ['numero_guia'], unique=False)
    
    # Create Batches table
    op.create_table(
        'tiss_batches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('numero_lote', sa.String(20), nullable=False),
        sa.Column('data_envio', sa.Date(), nullable=False),
        sa.Column('hora_envio', sa.String(5), nullable=True),
        sa.Column('guias_ids', sa.JSON(), nullable=False),
        sa.Column('guias_tipo', sa.String(20), nullable=False),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('hash_integridade', sa.String(64), nullable=True),
        sa.Column('submission_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('submission_method', sa.String(20), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('last_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('protocol_number', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('valor_total_lote', sa.Numeric(12, 2), nullable=True),
        sa.Column('versao_tiss', sa.String(20), nullable=False, server_default='3.05.02'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_batches_clinic_id', 'tiss_batches', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_batches_numero_lote', 'tiss_batches', ['numero_lote'], unique=False)
    op.create_index('ix_tiss_batches_submission_status', 'tiss_batches', ['submission_status'], unique=False)
    
    # Create Statements table
    op.create_table(
        'tiss_statements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('batch_id', sa.Integer(), nullable=True),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('tipo_demonstrativo', sa.String(50), nullable=False),
        sa.Column('numero_protocolo', sa.String(100), nullable=True),
        sa.Column('xml_recebido', sa.Text(), nullable=False),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('status_processamento', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('data_recebimento', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['tiss_batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_statements_batch_id', 'tiss_statements', ['batch_id'], unique=False)
    op.create_index('ix_tiss_statements_clinic_id', 'tiss_statements', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_statements_tipo_demonstrativo', 'tiss_statements', ['tipo_demonstrativo'], unique=False)
    
    # Create Attachments table
    op.create_table(
        'tiss_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('guide_id', sa.Integer(), nullable=False),
        sa.Column('guide_type', sa.String(50), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('hash_file', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_attachments_guide_id', 'tiss_attachments', ['guide_id'], unique=False)
    op.create_index('ix_tiss_attachments_guide_type', 'tiss_attachments', ['guide_type'], unique=False)
    
    # Create Audit Logs table (immutable)
    op.create_table(
        'tiss_audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('clinic_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('changes', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['clinic_id'], ['clinics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tiss_audit_logs_clinic_id', 'tiss_audit_logs', ['clinic_id'], unique=False)
    op.create_index('ix_tiss_audit_logs_user_id', 'tiss_audit_logs', ['user_id'], unique=False)
    op.create_index('ix_tiss_audit_logs_entity_type_id', 'tiss_audit_logs', ['entity_type', 'entity_id'], unique=False)
    op.create_index('ix_tiss_audit_logs_created_at', 'tiss_audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_tiss_audit_logs_created_at', table_name='tiss_audit_logs')
    op.drop_index('ix_tiss_audit_logs_entity_type_id', table_name='tiss_audit_logs')
    op.drop_index('ix_tiss_audit_logs_user_id', table_name='tiss_audit_logs')
    op.drop_index('ix_tiss_audit_logs_clinic_id', table_name='tiss_audit_logs')
    op.drop_table('tiss_audit_logs')
    
    op.drop_index('ix_tiss_attachments_guide_type', table_name='tiss_attachments')
    op.drop_index('ix_tiss_attachments_guide_id', table_name='tiss_attachments')
    op.drop_table('tiss_attachments')
    
    op.drop_index('ix_tiss_statements_tipo_demonstrativo', table_name='tiss_statements')
    op.drop_index('ix_tiss_statements_clinic_id', table_name='tiss_statements')
    op.drop_index('ix_tiss_statements_batch_id', table_name='tiss_statements')
    op.drop_table('tiss_statements')
    
    op.drop_index('ix_tiss_batches_submission_status', table_name='tiss_batches')
    op.drop_index('ix_tiss_batches_numero_lote', table_name='tiss_batches')
    op.drop_index('ix_tiss_batches_clinic_id', table_name='tiss_batches')
    op.drop_table('tiss_batches')
    
    op.drop_index('ix_tiss_individual_fees_numero_guia', table_name='tiss_individual_fees')
    op.drop_index('ix_tiss_individual_fees_clinic_id', table_name='tiss_individual_fees')
    op.drop_table('tiss_individual_fees')
    
    op.drop_index('ix_tiss_hospitalization_guides_status', table_name='tiss_hospitalization_guides')
    op.drop_index('ix_tiss_hospitalization_guides_numero_guia', table_name='tiss_hospitalization_guides')
    op.drop_index('ix_tiss_hospitalization_guides_clinic_id', table_name='tiss_hospitalization_guides')
    op.drop_table('tiss_hospitalization_guides')
    
    op.drop_index('ix_tiss_sadt_guides_status', table_name='tiss_sadt_guides')
    op.drop_index('ix_tiss_sadt_guides_numero_guia', table_name='tiss_sadt_guides')
    op.drop_index('ix_tiss_sadt_guides_clinic_id', table_name='tiss_sadt_guides')
    op.drop_table('tiss_sadt_guides')
    
    op.drop_index('ix_tiss_consultation_guides_invoice_id', table_name='tiss_consultation_guides')
    op.drop_index('ix_tiss_consultation_guides_status', table_name='tiss_consultation_guides')
    op.drop_index('ix_tiss_consultation_guides_numero_guia', table_name='tiss_consultation_guides')
    op.drop_index('ix_tiss_consultation_guides_clinic_id', table_name='tiss_consultation_guides')
    op.drop_table('tiss_consultation_guides')
    
    op.drop_index('ix_tiss_tuss_version_history_tuss_code_id', table_name='tiss_tuss_version_history')
    op.drop_table('tiss_tuss_version_history')
    
    op.drop_index('ix_tiss_tuss_codes_codigo_tabela', table_name='tiss_tuss_codes')
    op.drop_index('ix_tiss_tuss_codes_tabela', table_name='tiss_tuss_codes')
    op.drop_index('ix_tiss_tuss_codes_codigo', table_name='tiss_tuss_codes')
    op.drop_table('tiss_tuss_codes')
    
    op.drop_index('ix_tiss_versions_version', table_name='tiss_versions')
    op.drop_table('tiss_versions')

