"""Initial schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "observation_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("storage_path", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(op.f("ix_observation_sessions_mode"), "observation_sessions", ["mode"], unique=False)
    op.create_index(op.f("ix_observation_sessions_status"), "observation_sessions", ["status"], unique=False)

    op.create_table(
        "managed_files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("relative_path", sa.String(length=255), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["observation_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("relative_path"),
    )
    op.create_index(op.f("ix_managed_files_kind"), "managed_files", ["kind"], unique=False)
    op.create_index(op.f("ix_managed_files_session_id"), "managed_files", ["session_id"], unique=False)
    op.create_index(op.f("ix_managed_files_state"), "managed_files", ["state"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_managed_files_state"), table_name="managed_files")
    op.drop_index(op.f("ix_managed_files_session_id"), table_name="managed_files")
    op.drop_index(op.f("ix_managed_files_kind"), table_name="managed_files")
    op.drop_table("managed_files")
    op.drop_index(op.f("ix_observation_sessions_status"), table_name="observation_sessions")
    op.drop_index(op.f("ix_observation_sessions_mode"), table_name="observation_sessions")
    op.drop_table("observation_sessions")

