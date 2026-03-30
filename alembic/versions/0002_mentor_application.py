"""Add mentor_applications table for 4-step application form

Revision ID: 0002_mentor_application
Revises: 0003_mentor_verification
Create Date: 2026-03-23 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_mentor_application"
down_revision: Union[str, None] = "0003_mentor_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create mentor_applications table
    op.create_table(
        "mentor_applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        
        # Step 1: Personal Information
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("step_1_completed", sa.Boolean, server_default="0"),
        
        # Step 2: Professional Background
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("years_experience", sa.Integer, nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("professional_bio", sa.Text, nullable=True),
        sa.Column("step_2_completed", sa.Boolean, server_default="0"),
        
        # Step 3: Document Upload
        sa.Column("id_document_url", sa.String(512), nullable=True),
        sa.Column("id_document_type", sa.String(50), nullable=True),
        sa.Column("professional_certificate_url", sa.String(512), nullable=True),
        sa.Column("step_3_completed", sa.Boolean, server_default="0"),
        
        # Step 4: Review and Submit
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.Enum("draft", "step_1", "step_2", "step_3", "review", "submitted", "approved", "rejected"), server_default="draft"),
        
        # Admin review
        sa.Column("admin_notes", sa.Text, nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("reviewed_by", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    
    # Create indexes
    op.create_index("ix_mentor_applications_mentor_id", "mentor_applications", ["mentor_id"])
    op.create_index("ix_mentor_applications_status", "mentor_applications", ["status"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_mentor_applications_status", table_name="mentor_applications")
    op.drop_index("ix_mentor_applications_mentor_id", table_name="mentor_applications")
    
    # Drop table
    op.drop_table("mentor_applications")
