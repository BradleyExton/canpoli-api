"""add riding name+province index

Revision ID: 1b2c3d4e5f6a
Revises: 9b7a2d7f2c3a
Create Date: 2026-02-07 09:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "1b2c3d4e5f6a"
down_revision: Union[str, None] = "9b7a2d7f2c3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_ridings_name_province",
        "ridings",
        ["name", "province"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ridings_name_province", table_name="ridings")
