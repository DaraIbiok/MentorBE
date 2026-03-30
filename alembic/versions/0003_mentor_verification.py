"""Add verification_status to users for mentor verification flow."""

from typing import Union, Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0003_mentor_verification"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "verification_status",
            sa.Enum("not_required", "pending", "approved", "rejected"),
            nullable=False,
            server_default="not_required",
        ),
    )
    # All existing mentors get approved automatically (they were already active)
    op.execute(
        "UPDATE users SET verification_status = 'approved' WHERE role = 'mentor'"
    )
    # All existing mentees and admins get not_required
    op.execute(
        "UPDATE users SET verification_status = 'not_required' WHERE role != 'mentor'"
    )


def downgrade() -> None:
    op.drop_column("users", "verification_status")