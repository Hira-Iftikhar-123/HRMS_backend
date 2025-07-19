from pydantic import BaseModel

class RoleResponse(BaseModel):
    class Config:
        from_attributes = True
    id: int
    name: str 