from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    school_id: int
    full_name: Optional[str] = None
    role: Optional[str] = "student"


class LoginIn(BaseModel):
    email: EmailStr
    password: str
    school_id: int


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
