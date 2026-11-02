from sqlalchemy import Boolean, Column, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.base import Base


class WasteTreatment(Base):
    __tablename__ = "waste_treatments"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False, server_default=func.gen_random_uuid())
    name = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

    __table_args__ = (
        UniqueConstraint("name", name="waste_treatments_name_key"),
    )
