from pydantic import BaseModel, ConfigDict, Field
from models.user import UserRole


class UserRegister(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: UserRole
    is_blocked: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
