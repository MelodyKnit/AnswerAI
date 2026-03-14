from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    role: str = Field(pattern="^(student|teacher)$")
    name: str
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str | None = None
    school_name: str | None = None
    grade_name: str | None = None
    teacher_invite_code: str | None = None
    class_code: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    school_name: str | None = None
    grade_name: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
