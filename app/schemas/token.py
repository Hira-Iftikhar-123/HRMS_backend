from pydantic import BaseModel

class Token(BaseModel):
    model_config = {
        "from_attributes": True
    }
    access_token: str
    token_type: str 
    role: str