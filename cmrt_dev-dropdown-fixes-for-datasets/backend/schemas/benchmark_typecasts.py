from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class BenchmarkTypecastBase(BaseModel):
    code: str
    name: str
    mastertype_id: UUID


class BenchmarkTypecastCreate(BenchmarkTypecastBase):
    pass


class BenchmarkTypecastOut(BenchmarkTypecastBase):
    id: UUID
    mastertype_name: Optional[str] = None

    class Config:
        from_attributes = True
