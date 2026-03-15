from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    role: str = Field(pattern="^(student|teacher)$")
    name: str
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9]+$")
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    phone: str | None = None
    school_name: str | None = None
    grade_name: str | None = None
    teacher_invite_code: str | None = None
    class_code: str | None = None

    @model_validator(mode="after")
    def validate_username_and_password(self):
        """
        处理 validate username and password 请求并返回结果。
        """
        if not any(ch.isalpha() for ch in self.username):
            raise ValueError("Username must contain letters and can include numbers")
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password do not match")
        return self


class LoginRequest(BaseModel):
    login_id: str
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
