from sqlalchemy import Column, String, SmallInteger
from core.base import Base


class GhgScope(Base):
    __tablename__ = "ghg_scopes"

    # SmallInteger PK as per DBML (id smallint [pk]) — fixed 3 rows, no UUID
    id = Column(SmallInteger, primary_key=True, autoincrement=False)
    name = Column(String, nullable=False)
