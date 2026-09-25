from sqlalchemy import Column, String, Text

from core.base import Base


class LifecycleModule(Base):
    __tablename__ = "lifecycle_modules"

    # String primary key is intentional: lifecycle module codes are semantic identifiers
    # (e.g. "A1", "B6") used directly in business logic and API responses.
    # Using UUID here would add no value and break the lookup-by-code pattern throughout the codebase.
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
