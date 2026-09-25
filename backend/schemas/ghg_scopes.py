from pydantic import BaseModel


class GhgScopeOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
