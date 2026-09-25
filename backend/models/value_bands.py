from sqlalchemy import Column, SmallInteger, String

from core.base import Base


class ValueBand(Base):
    __tablename__ = "value_bands"

    # String primary key is intentional: value band codes are short semantic identifiers
    # (e.g. "LOW", "MED", "HIGH") displayed directly in the UI and used as lookup keys.
    code = Column(String, primary_key=True)
    sort_order = Column(SmallInteger, nullable=True)
