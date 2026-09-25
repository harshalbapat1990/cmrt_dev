import uuid as _uuid

from sqlalchemy import Column, String, Boolean, TIMESTAMP, Date, Integer, Numeric, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from core.base import Base

class ProjectClass(PyEnum):
    SMALL = "SMALL"
    LARGE = "LARGE"
    RECURRING = "RECURRING"

class Project(Base):
    __tablename__ = "project"
    __table_args__ = (
        UniqueConstraint("project_name", name="uq_project_project_name"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=_uuid.uuid4, server_default=text("gen_random_uuid()"))
   
    project_name = Column(String(200), nullable=False)
    # Foreign keys to benchmark tables (replaces legacy project_type and project_typecast strings)
    project_type_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_mastertypes.id"), nullable=True)
    project_typecast_id = Column(UUID(as_uuid=True), ForeignKey("benchmark_typecasts.id"), nullable=True)
    description = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True)
    created_on = Column(TIMESTAMP(timezone=False), server_default=func.now())
    updated_on = Column(TIMESTAMP(timezone=False), nullable=True)

   
    project_class = Column(Enum(ProjectClass, name="project_class", create_type=False), nullable=False)
    simple_carbon_assessment = Column(Boolean, default=False)
    contract_number = Column(String(100), nullable=True, default="")
    design_contract_number = Column(String(100), nullable=True)
    construction_contract_number = Column(String(100), nullable=True)
    program_name = Column(String(255), nullable=True)
    location_text = Column(String(255), nullable=True)

    construction_start_date = Column(Date, nullable=True)
    construction_end_date = Column(Date, nullable=True)
    commencement_of_operations = Column(Date, nullable=True)
    operational_life_years = Column(Integer, nullable=True)
    project_capex_million = Column(Numeric(18, 2), nullable=True)
    project_opex = Column(Numeric(18, 2), nullable=True)
    declared_unit_value = Column(Numeric(18, 4), nullable=True)
    declared_unit_type = Column(String(50), nullable=True)

    first_submission_month = Column(Date, nullable=True) 
    maintenance_region = Column(String(255), nullable=True)

    proponent_org_id = Column(UUID(as_uuid=True), ForeignKey("organization.id"), nullable=False)

    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    last_updated_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    stage_configs = relationship("ProjectStageConfig", cascade="all, delete-orphan")
    org_links = relationship("ProjectOrganization", cascade="all, delete-orphan")
    postcodes = relationship("ProjectPostcode", cascade="all, delete-orphan")
    stage_instances = relationship("ProjectStageInstance", cascade="all, delete-orphan")
    project_parties = relationship("ProjectParty", cascade="all, delete-orphan")
    reporting_boundaries = relationship("ProjectReportingBoundary", cascade="all, delete-orphan", order_by="ProjectReportingBoundary.sort_order")
    benchmark_mastertype = relationship("BenchmarkMastertype", foreign_keys=[project_type_id])
    benchmark_typecast = relationship("BenchmarkTypecast", foreign_keys=[project_typecast_id])
