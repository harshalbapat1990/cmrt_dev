
from sqlalchemy.orm import DeclarativeBase, declared_attr
from sqlalchemy import MetaData
from sqlalchemy.sql import func
from sqlalchemy import Column
from sqlalchemy.types import TIMESTAMP

# Optional: enforce a naming convention for constraints & indexes.
# This helps migrations (Alembic) and keeps names consistent across environments.
NAMING_CONVENTION = {
    "ix": "ix__%(table_name)s__%(column_0_N_name)s",
    "uq": "uq__%(table_name)s__%(column_0_N_name)s",
    "ck": "ck__%(table_name)s__%(constraint_name)s",
    "fk": "fk__%(table_name)s__%(column_0_N_name)s__%(referred_table_name)s",
    "pk": "pk__%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base all models inherit from."""
    metadata = metadata

    # # Optional: auto-generate __tablename__ based on class name (snake_case)
    # # If you prefer explicit __tablename__ in each model, remove this block.
    # @declared_attr.directive
    # def __tablename__(cls) -> str:
    #     # Convert CamelCase to snake_case (simple heuristic)
    #     import re
    #     name = cls.__name__
    #     s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    #     return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class TimestampMixin:
    """Add created_on / updated_on columns (UTC, no timezone)."""
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now(), nullable=True)
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)

    # If you want automatic updated_on on UPDATE, you can use:
    # updated_on = Column(TIMESTAMP(timezone=False), server_default=func.now(), onupdate=func.now())


# If many tables use UUID PKs with server-generated values, you can add a mixin:
# (Note: Your schema already defines UUID PKs at the DB level; for inserts
#  from the app side you often set them in Python using uuid4().)
"""
from sqlalchemy.dialects.postgresql import UUID
from uuid import uuid4

class UUIDPrimaryKeyMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
"""
