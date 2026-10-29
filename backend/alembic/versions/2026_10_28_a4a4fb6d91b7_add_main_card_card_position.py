"""add main_card card position

Revision ID: a4a4fb6d91b7
Revises: d0012cc70d4e
Create Date: 2026-10-28 21:05:40.927642

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4a4fb6d91b7"
down_revision: str | None = "d0012cc70d4e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Autogenerate doesn't detect new enum values, so this migration is written by hand.
    op.execute("ALTER TYPE card_position ADD VALUE IF NOT EXISTS 'main_card' AFTER 'co_main'")


def downgrade() -> None:
    # Postgres can't remove a value from an enum, so rebuild the type without it.
    # Bouts marked main_card become prelim, the closest remaining value.
    op.execute("UPDATE bouts SET card_position = 'prelim' WHERE card_position = 'main_card'")
    op.execute("ALTER TYPE card_position RENAME TO card_position_old")
    op.execute("CREATE TYPE card_position AS ENUM ('main', 'co_main', 'prelim')")
    op.execute(
        "ALTER TABLE bouts ALTER COLUMN card_position "
        "TYPE card_position USING card_position::text::card_position"
    )
    op.execute("DROP TYPE card_position_old")
