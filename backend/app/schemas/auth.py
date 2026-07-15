"""Auth schemas — registration, login, token responses."""

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str | None = None


from uuid import UUID

class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    is_active: bool

    model_config = {"from_attributes": True}
