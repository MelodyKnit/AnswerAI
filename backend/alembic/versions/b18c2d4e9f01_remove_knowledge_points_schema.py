"""remove knowledge_points schema

Revision ID: b18c2d4e9f01
Revises: 3d9f8a1b7c2e
Create Date: 2026-03-19 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b18c2d4e9f01"
down_revision: Union[str, Sequence[str], None] = "3d9f8a1b7c2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    columns = [col.get("name") for col in inspector.get_columns(table_name)]
    return column_name in columns


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    indexes = [idx.get("name") for idx in inspector.get_indexes(table_name)]
    return index_name in indexes


def upgrade() -> None:
    # Cleanup in case a previous SQLite batch migration failed and left temp table behind.
    if _has_table("_alembic_tmp_study_tasks"):
        op.execute("DROP TABLE _alembic_tmp_study_tasks")

    if _has_index("study_tasks", "ix_study_tasks_knowledge_point_id"):
        op.drop_index("ix_study_tasks_knowledge_point_id", table_name="study_tasks")

    if _has_column("study_tasks", "knowledge_point_id"):
        with op.batch_alter_table("study_tasks") as batch_op:
            batch_op.drop_column("knowledge_point_id")

    if _has_table("question_knowledge_points"):
        op.drop_table("question_knowledge_points")

    if _has_table("knowledge_mastery_snapshots"):
        op.drop_table("knowledge_mastery_snapshots")

    if _has_table("knowledge_points"):
        op.drop_table("knowledge_points")


def downgrade() -> None:
    if not _has_table("knowledge_points"):
        op.create_table(
            "knowledge_points",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("name", sa.String(length=150), nullable=False),
            sa.Column("path", sa.String(length=500), nullable=False),
            sa.Column("level", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
            sa.ForeignKeyConstraint(["parent_id"], ["knowledge_points.id"]),
        )
        op.create_index("ix_knowledge_points_subject_id", "knowledge_points", ["subject_id"], unique=False)
        op.create_index("ix_knowledge_points_parent_id", "knowledge_points", ["parent_id"], unique=False)
        op.create_index("ix_knowledge_points_level", "knowledge_points", ["level"], unique=False)
        op.create_index("ix_knowledge_points_name", "knowledge_points", ["name"], unique=False)
        op.create_index("ix_knowledge_points_path", "knowledge_points", ["path"], unique=False)
        op.create_index("ix_knowledge_points_status", "knowledge_points", ["status"], unique=False)

    if not _has_table("question_knowledge_points"):
        op.create_table(
            "question_knowledge_points",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("knowledge_point_id", sa.Integer(), nullable=False),
            sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
            sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"]),
            sa.UniqueConstraint("question_id", "knowledge_point_id", name="uq_question_knowledge"),
        )
        op.create_index("ix_question_knowledge_points_question_id", "question_knowledge_points", ["question_id"], unique=False)
        op.create_index("ix_question_knowledge_points_knowledge_point_id", "question_knowledge_points", ["knowledge_point_id"], unique=False)

    if not _has_table("knowledge_mastery_snapshots"):
        op.create_table(
            "knowledge_mastery_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("owner_type", sa.String(length=20), nullable=False),
            sa.Column("owner_id", sa.Integer(), nullable=False),
            sa.Column("subject_id", sa.Integer(), nullable=False),
            sa.Column("knowledge_point_id", sa.Integer(), nullable=False),
            sa.Column("mastery_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("wrong_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_exam_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["subject_id"], ["subjects.id"]),
            sa.ForeignKeyConstraint(["knowledge_point_id"], ["knowledge_points.id"]),
            sa.ForeignKeyConstraint(["source_exam_id"], ["exams.id"]),
        )
        op.create_index("ix_knowledge_mastery_snapshots_owner_type", "knowledge_mastery_snapshots", ["owner_type"], unique=False)
        op.create_index("ix_knowledge_mastery_snapshots_owner_id", "knowledge_mastery_snapshots", ["owner_id"], unique=False)
        op.create_index("ix_knowledge_mastery_snapshots_subject_id", "knowledge_mastery_snapshots", ["subject_id"], unique=False)
        op.create_index("ix_knowledge_mastery_snapshots_knowledge_point_id", "knowledge_mastery_snapshots", ["knowledge_point_id"], unique=False)
        op.create_index("ix_knowledge_mastery_snapshots_mastery_score", "knowledge_mastery_snapshots", ["mastery_score"], unique=False)
        op.create_index("ix_knowledge_mastery_snapshots_source_exam_id", "knowledge_mastery_snapshots", ["source_exam_id"], unique=False)

    if not _has_column("study_tasks", "knowledge_point_id"):
        with op.batch_alter_table("study_tasks") as batch_op:
            batch_op.add_column(sa.Column("knowledge_point_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key("fk_study_tasks_knowledge_point_id", "knowledge_points", ["knowledge_point_id"], ["id"])
            batch_op.create_index("ix_study_tasks_knowledge_point_id", ["knowledge_point_id"], unique=False)
