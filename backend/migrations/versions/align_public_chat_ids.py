"""Align public chat conversation ID columns.

Revision ID: align_public_chat_ids
Revises: b6d0bd8fa816
Create Date: 2026-07-30

This migration standardizes public-chat conversation IDs as VARCHAR(50).

It intentionally preserves legacy string identifiers such as:
- short hexadecimal IDs
- conv_* widget IDs
- full UUID strings

It does not use the unsafe migrate_uuid.py script.
"""

from alembic import context, op
import sqlalchemy as sa


revision = "align_public_chat_ids"
down_revision = "b6d0bd8fa816"
branch_labels = None
depends_on = None


def upgrade():
    # Live data checks cannot execute in Alembic offline SQL mode.
    # They still run before every real online migration.
    if not context.is_offline_mode():
        connection = op.get_bind()

        # Refuse to truncate an existing ID silently.
        for table_name in (
            "contact_info",
            "conversation_history",
            "conversation_state",
        ):
            overlength_count = connection.execute(
                sa.text(
                    f"""
                    SELECT COUNT(*)
                    FROM {table_name}
                    WHERE conversation_id IS NOT NULL
                      AND LENGTH(conversation_id) > 50
                    """
                )
            ).scalar_one()

            if overlength_count:
                raise RuntimeError(
                    f"{table_name} contains {overlength_count} "
                    "conversation IDs longer than 50 characters."
                )

        # contact_info must have one non-null ID for every lead record.
        null_contact_ids = connection.execute(
            sa.text(
                """
                SELECT COUNT(*)
                FROM contact_info
                WHERE conversation_id IS NULL
                """
            )
        ).scalar_one()

        if null_contact_ids:
            raise RuntimeError(
                "contact_info contains rows with null conversation IDs."
            )


    # Drop the dependent FK before changing both column types.
    op.drop_constraint(
        "conversation_history_conversation_id_fkey",
        "conversation_history",
        type_="foreignkey",
    )

    op.alter_column(
        "contact_info",
        "conversation_id",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
        nullable=False,
        postgresql_using="conversation_id::varchar(50)",
    )

    op.alter_column(
        "conversation_history",
        "conversation_id",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=False,
        nullable=False,
        postgresql_using="conversation_id::varchar(50)",
    )

    op.alter_column(
        "conversation_state",
        "conversation_id",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=False,
        nullable=False,
        postgresql_using="conversation_id::varchar(50)",
    )

    op.create_foreign_key(
        "conversation_history_conversation_id_fkey",
        "conversation_history",
        "contact_info",
        ["conversation_id"],
        ["conversation_id"],
        ondelete="CASCADE",
    )

    # ConversationState must contain at most one row per conversation.
    op.create_index(
        "ix_conversation_state_conversation_id",
        "conversation_state",
        ["conversation_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_conversation_state_conversation_id",
        table_name="conversation_state",
    )

    op.drop_constraint(
        "conversation_history_conversation_id_fkey",
        "conversation_history",
        type_="foreignkey",
    )

    op.alter_column(
        "conversation_state",
        "conversation_id",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=False,
        postgresql_using="conversation_id::text",
    )

    op.alter_column(
        "conversation_history",
        "conversation_id",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=False,
        postgresql_using="conversation_id::text",
    )

    op.alter_column(
        "contact_info",
        "conversation_id",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=False,
        nullable=True,
        postgresql_using="conversation_id::text",
    )

    op.create_foreign_key(
        "conversation_history_conversation_id_fkey",
        "conversation_history",
        "contact_info",
        ["conversation_id"],
        ["conversation_id"],
        ondelete="CASCADE",
    )
