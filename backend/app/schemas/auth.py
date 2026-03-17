from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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
            raise ValueError("用户名必须包含英文字母，可使用英文+数字组合")
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginRequest(BaseModel):
    login_id: str
    password: str


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    avatar_url: str | None = None
    school_name: str | None = None
    grade_name: str | None = None

    @model_validator(mode="after")
    def validate_username_immutable(self):
        if self.username is not None:
            raise ValueError("用户名一旦设置后不可修改")
        return self


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserFeedbackCreateRequest(BaseModel):
    category: str = Field(pattern="^(bug|product|design|other)$")
    content: str = Field(min_length=5, max_length=2000)
    images: list[str] = Field(default_factory=list, max_length=6)
    page_path: str | None = Field(default=None, max_length=255)
