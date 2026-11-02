from sqlalchemy import Column, SmallInteger, String

from core.base import Base


class GradeDefinition(Base):
    __tablename__ = "grade_definitions"

    id = Column(SmallInteger, primary_key=True, autoincrement=False)
    name = Column(String, nullable=False)
