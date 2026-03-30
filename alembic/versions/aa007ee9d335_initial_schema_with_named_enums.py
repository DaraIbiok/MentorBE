"""Initial schema with named enums

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create all named ENUM types first
    op.execute("CREATE TYPE user_role_enum AS ENUM('mentee', 'mentor', 'admin')")
    op.execute("CREATE TYPE verification_status_enum AS ENUM('not_required', 'pending', 'approved', 'rejected')")
    op.execute("CREATE TYPE request_status_enum AS ENUM('pending', 'accepted', 'declined')")
    op.execute("CREATE TYPE session_status_enum AS ENUM('scheduled', 'in_progress', 'completed', 'cancelled')")
    op.execute("CREATE TYPE notification_type_enum AS ENUM('message', 'session', 'request', 'system')")
    op.execute("CREATE TYPE application_status_enum AS ENUM('draft', 'step_1', 'step_2', 'step_3', 'review', 'submitted', 'approved', 'rejected')")
    
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supabase_id", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum(name="user_role_enum"), nullable=False, server_default="mentee"),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("goals", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("verification_status", sa.Enum(name="verification_status_enum"), nullable=False, server_default="not_required"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_supabase_id", "users", ["supabase_id"])
    op.create_index("ix_users_email", "users", ["email"])

    # Mentorship requests table
    op.create_table(
        "mentorship_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("preferred_time", sa.DateTime, nullable=True),
        sa.Column("status", sa.Enum(name="request_status_enum"), server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime, nullable=False),
        sa.Column("duration_minutes", sa.Integer, server_default="60"),
        sa.Column("status", sa.Enum(name="session_status_enum"), server_default="scheduled"),
        sa.Column("video_room_url", sa.String(512), nullable=True),
        sa.Column("video_room_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Session messages table
    op.create_table(
        "session_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Ratings table
    op.create_table(
        "ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("rater_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rated_user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("tags", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("session_id", "rater_id", name="uq_session_rater"),
    )
    
    # Notifications table
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.Enum(name="notification_type_enum"), nullable=False, server_default="system"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("read", sa.Boolean, server_default="false"),
        sa.Column("related_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    
    # Mentor applications table
    op.create_table(
        "mentor_applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        
        # Step 1: Personal Information
        sa.Column("phone_number", sa.String(20), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("step_1_completed", sa.Boolean, server_default="false"),
        
        # Step 2: Professional Background
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("years_experience", sa.Integer, nullable=True),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("professional_bio", sa.Text, nullable=True),
        sa.Column("step_2_completed", sa.Boolean, server_default="false"),
        
        # Step 3: Document Upload
        sa.Column("id_document_url", sa.String(512), nullable=True),
        sa.Column("id_document_type", sa.String(50), nullable=True),
        sa.Column("professional_certificate_url", sa.String(512), nullable=True),
        sa.Column("step_3_completed", sa.Boolean, server_default="false"),
        
        # Step 4: Review and Submit
        sa.Column("submitted_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.Enum(name="application_status_enum"), nullable=False, server_default="draft"),
        
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
    # Drop tables in reverse order
    op.drop_table("mentor_applications")
    op.drop_table("notifications")
    op.drop_table("ratings")
    op.drop_table("session_messages")
    op.drop_table("sessions")
    op.drop_table("mentorship_requests")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_supabase_id", table_name="users")
    op.drop_table("users")
    
    # Drop all enum types
    op.execute("DROP TYPE IF EXISTS application_status_enum")
    op.execute("DROP TYPE IF EXISTS notification_type_enum")
    op.execute("DROP TYPE IF EXISTS session_status_enum")
    op.execute("DROP TYPE IF EXISTS request_status_enum")
    op.execute("DROP TYPE IF EXISTS verification_status_enum")
    op.execute("DROP TYPE IF EXISTS user_role_enum")