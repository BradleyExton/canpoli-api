"""add PostGIS geometry to ridings

Revision ID: 9b7a2d7f2c3a
Revises: 6f626f339675
Create Date: 2026-02-06 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9b7a2d7f2c3a"
down_revision: Union[str, None] = "6f626f339675"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("ALTER TABLE ridings ADD COLUMN geom geometry(MULTIPOLYGON, 4326)")
    op.execute("CREATE INDEX ix_ridings_geom ON ridings USING GIST (geom)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ridings_geom")
    op.execute("ALTER TABLE ridings DROP COLUMN geom")
