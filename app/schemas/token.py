from pydantic import BaseModel

class Token(BaseModel):
    class Config:
        from_attributes = True
    access_token: str
    token_type: str 