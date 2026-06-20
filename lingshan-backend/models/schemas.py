#这是一个典型的用户认证系统的数据验证层，确保接口接收的数据格式正确且安全。
from pydantic import BaseModel, Field, validator
from validators import validate_phone, validate_password

class GetCodeForm(BaseModel):
    phone: str = Field("", max_length=11)
    code_type: str = Field("register", max_length=20)

    @validator('phone')
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v

    @validator('code_type')
    def check_code_type(cls, v):
        if v not in {"register", "login"}:
            raise ValueError('验证码类型不正确')
        return v

class RegisterForm(BaseModel):
    phone: str = Field("", max_length=11)
    code: str = Field("", min_length=4, max_length=6)
    password: str = Field("", max_length=20)
    confirm_password: str = Field("", max_length=20)

    @validator('phone')
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v

    @validator('password')
    def check_password(cls, v):
        valid, msg = validate_password(v)
        if not valid:
            raise ValueError(msg)
        return v

class LoginForm(BaseModel):
    phone: str = Field("", max_length=11)
    password: str = Field("", max_length=20)
    code: str = Field("", max_length=6)

    @validator('phone')
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v
