"""Custom geometry type for PostGIS."""

from __future__ import annotations

from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import UserDefinedType


class Geometry(UserDefinedType):
    """PostGIS geometry type wrapper for SQLAlchemy."""

    cache_ok = True

    def __init__(self, geometry_type: str = "MULTIPOLYGON", srid: int = 4326):
        self.geometry_type = geometry_type
        self.srid = srid

    def get_col_spec(self, **kw) -> str:  # type: ignore[override]
        return f"geometry({self.geometry_type},{self.srid})"


@compiles(Geometry, "sqlite")
def _compile_geometry_sqlite(type_: Geometry, compiler, **kw) -> str:
    return "BLOB"
