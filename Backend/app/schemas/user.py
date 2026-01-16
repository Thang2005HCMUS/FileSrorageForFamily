from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Optional

# Dùng cho API Đăng ký
class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)

# Dùng cho API Login (Response Token)
class Token(BaseModel):
    access_token: str
    token_type: str

# Dùng để trả về thông tin User (không trả password)
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    username: str
    root_folder_id: Optional[UUID]
    is_active: bool

    class Config:
        from_attributes = True