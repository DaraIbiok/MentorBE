"""Initial schema — create all tables

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("supabase_id", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("mentee", "mentor", "admin"), nullable=False, server_default="mentee"),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("bio", sa.Text, nullable=True),
        sa.Column("gender", sa.String(50), nullable=True),
        sa.Column("skills", sa.Text, nullable=True),
        sa.Column("goals", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_users_supabase_id", "users", ["supabase_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "mentorship_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=True),
        sa.Column("preferred_time", sa.DateTime, nullable=True),
        sa.Column("status", sa.Enum("pending", "accepted", "declined"), server_default="pending"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("mentor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mentee_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime, nullable=False),
        sa.Column("duration_minutes", sa.Integer, server_default="60"),
        sa.Column("status", sa.Enum("scheduled", "in_progress", "completed", "cancelled"), server_default="scheduled"),
        sa.Column("video_room_url", sa.String(512), nullable=True),
        sa.Column("video_room_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "session_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("sender_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

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


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_table("session_messages")
    op.drop_table("sessions")
    op.drop_table("mentorship_requests")
    op.drop_index("ix_users_email", "users")
    op.drop_index("ix_users_supabase_id", "users")
    op.drop_table("users")
