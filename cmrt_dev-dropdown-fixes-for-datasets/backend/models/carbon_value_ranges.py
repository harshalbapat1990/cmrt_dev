from sqlalchemy import Column, String, Index

from core.base import Base


class CarbonValueRange(Base):
    __tablename__ = "carbon_value_ranges"

    code = Column(String(50), primary_key=True, nullable=False)
    name = Column(String(100), nullable=False)

    __table_args__ = (
        Index("ix_cvr_code", "code"),
    )
