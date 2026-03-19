from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


revision = "0001_accounts_system"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(conn, table_name: str) -> bool:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        return conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        ).first() is not None
    return conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_name=:name
            """
        ),
        {"name": table_name},
    ).first() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return any(r[1] == column_name for r in rows)
    return conn.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name=:table_name AND column_name=:column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).first() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # Accounts table
    if not _table_exists(bind, "accounts"):
        op.create_table(
            "accounts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("type", sa.String(length=20), nullable=False),
            sa.Column("initial_balance", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("current_balance", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )

    # transaction.account_id
    if not _column_exists(bind, "transactions", "account_id"):
        op.add_column("transactions", sa.Column("account_id", sa.Integer(), nullable=True))

        # Create default cash account per user for backfill.
        bind.execute(
            text(
                """
                INSERT INTO accounts (user_id, name, type, initial_balance, current_balance, created_at)
                SELECT u.id, 'Carteira', 'cash', 0.0, 0.0, CURRENT_TIMESTAMP
                FROM users u
                WHERE NOT EXISTS (
                    SELECT 1 FROM accounts a
                    WHERE a.user_id = u.id AND a.name = 'Carteira' AND a.type = 'cash'
                )
                """
            )
        )

        bind.execute(
            text(
                """
                UPDATE transactions
                SET account_id = (
                    SELECT a.id
                    FROM accounts a
                    WHERE a.user_id = transactions.user_id
                      AND a.name = 'Carteira'
                      AND a.type = 'cash'
                    LIMIT 1
                )
                WHERE account_id IS NULL
                """
            )
        )

    # Transfers table
    if not _table_exists(bind, "transfers"):
        op.create_table(
            "transfers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False, index=True),
            sa.Column("from_account_id", sa.Integer(), nullable=False, index=True),
            sa.Column("to_account_id", sa.Integer(), nullable=False, index=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("date", sa.DateTime(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("transfer_group", sa.String(length=64), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"]),
            sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"]),
        )


def downgrade() -> None:
    # Not intended to be used in this project lifecycle.
    # Alembic requires a downgrade function; we keep it explicit.
    pass

