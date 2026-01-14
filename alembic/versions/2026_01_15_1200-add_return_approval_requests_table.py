"""add_return_approval_requests_table

Revision ID: add_return_approval_requests
Revises: 1d8b34150b42
Create Date: 2026-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'add_return_approval_requests'
down_revision: Union[str, None] = '1d8b34150b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ReturnApprovalStatus enum if it doesn't exist
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'returnapprovalstatus') THEN
                CREATE TYPE returnapprovalstatus AS ENUM ('pending', 'approved', 'rejected', 'expired');
            END IF;
        END $$;
    """)
    
    # Check if table already exists before creating
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'return_approval_requests'
            ) THEN
                CREATE TABLE return_approval_requests (
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER NOT NULL,
                    doctor_id INTEGER NOT NULL,
                    clinic_id INTEGER NOT NULL,
                    requested_appointment_date TIMESTAMP WITH TIME ZONE NOT NULL,
                    appointment_type VARCHAR(100) NOT NULL DEFAULT 'retorno',
                    notes TEXT,
                    returns_count_this_month INTEGER NOT NULL DEFAULT 0,
                    status returnapprovalstatus NOT NULL DEFAULT 'pending',
                    requested_by INTEGER NOT NULL,
                    approved_by INTEGER,
                    approval_notes TEXT,
                    resulting_appointment_id INTEGER,
                    requested_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    reviewed_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
                    updated_at TIMESTAMP WITH TIME ZONE,
                    CONSTRAINT fk_return_approval_requests_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
                    CONSTRAINT fk_return_approval_requests_doctor FOREIGN KEY (doctor_id) REFERENCES users(id),
                    CONSTRAINT fk_return_approval_requests_clinic FOREIGN KEY (clinic_id) REFERENCES clinics(id),
                    CONSTRAINT fk_return_approval_requests_requested_by FOREIGN KEY (requested_by) REFERENCES users(id),
                    CONSTRAINT fk_return_approval_requests_approved_by FOREIGN KEY (approved_by) REFERENCES users(id),
                    CONSTRAINT fk_return_approval_requests_appointment FOREIGN KEY (resulting_appointment_id) REFERENCES appointments(id)
                );
                
                CREATE INDEX ix_return_approval_requests_id ON return_approval_requests(id);
                CREATE INDEX ix_return_approval_requests_patient_id ON return_approval_requests(patient_id);
                CREATE INDEX ix_return_approval_requests_doctor_id ON return_approval_requests(doctor_id);
                CREATE INDEX ix_return_approval_requests_clinic_id ON return_approval_requests(clinic_id);
                CREATE INDEX ix_return_approval_requests_status ON return_approval_requests(status);
                CREATE INDEX ix_return_approval_requests_resulting_appointment_id ON return_approval_requests(resulting_appointment_id);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_resulting_appointment_id")
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_status")
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_clinic_id")
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_doctor_id")
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_patient_id")
    op.execute("DROP INDEX IF EXISTS ix_return_approval_requests_id")
    op.execute("DROP TABLE IF EXISTS return_approval_requests")
    op.execute("DROP TYPE IF EXISTS returnapprovalstatus")
