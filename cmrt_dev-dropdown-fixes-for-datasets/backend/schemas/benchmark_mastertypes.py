from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class BenchmarkMastertypeBase(BaseModel):
    code: str
    name: str


class BenchmarkMastertypeCreate(BenchmarkMastertypeBase):
    pass


class BenchmarkMastertypeOut(BenchmarkMastertypeBase):
    id: UUID

    class Config:
        from_attributes = True
