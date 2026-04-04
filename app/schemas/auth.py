from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    school_id: Optional[int] = None
    full_name: Optional[str] = None
    role: Optional[str] = "student"


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    school_id: Optional[int] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
