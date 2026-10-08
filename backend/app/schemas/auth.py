from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = "Supply Chain Operator"
    role: Optional[str] = "OPERATIONS_LEAD"


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
