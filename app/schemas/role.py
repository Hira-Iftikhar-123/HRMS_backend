from pydantic import BaseModel

class RoleResponse(BaseModel):
    model_config = {
        "from_attributes": True
    }
    id: int
    name: str 