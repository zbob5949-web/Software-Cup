from pydantic import BaseModel, field_validator
from app.validators import validate_phone, validate_password

class GetCodeForm(BaseModel):
    phone: str = ""
    code_type: str = "register"

    @field_validator('phone')
    @classmethod
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v

class RegisterForm(BaseModel):
    phone: str = ""
    code: str = ""
    password: str = ""
    confirm_password: str = ""

    @field_validator('phone')
    @classmethod
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v

    @field_validator('password')
    @classmethod
    def check_password(cls, v):
        valid, msg = validate_password(v)
        if not valid:
            raise ValueError(msg)
        return v

class LoginForm(BaseModel):
    phone: str = ""
    password: str = ""
    code: str = ""

    @field_validator('phone')
    @classmethod
    def check_phone(cls, v):
        if not v:  # 允许空字符串（游客模式等场景）
            return v
        if v in ('admin', 'user'):  # 管理员或测试用户名登录
            return v
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v