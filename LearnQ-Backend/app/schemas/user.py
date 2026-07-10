from pydantic import BaseModel, EmailStr
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None
    role: Optional[str] = 'user'

class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int

    class Config:
        from_attributes  = True