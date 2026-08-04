from sqlalchemy import text


def ensure_runtime_schema(engine) -> None:
    """Add backward-compatible columns missing from older databases."""
    statements = (
        """
        ALTER TABLE conversation_history
        ADD COLUMN IF NOT EXISTS user_id INTEGER
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS is_online
        BOOLEAN NOT NULL DEFAULT FALSE
        """,
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMPTZ
        """,
        """
        CREATE INDEX IF NOT EXISTS ix_conversation_history_user_id
        ON conversation_history (user_id)
        """,
    )

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

    print("✅ Runtime database schema verified")
