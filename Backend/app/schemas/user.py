from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)

class Token(BaseModel):
    access_token: str
    token_type: str

class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    root_folder_id: Optional[UUID]
    is_active: bool
    class Config:
        from_attributes = True