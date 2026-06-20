from pydantic import BaseModel, validator
from app.validators import validate_phone, validate_password

class GetCodeForm(BaseModel):
    phone: str = ""
    code_type: str = "register"

    @validator('phone')
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v

class RegisterForm(BaseModel):
    phone: str = ""
    code: str = ""
    password: str = ""
    confirm_password: str = ""

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
    phone: str = ""
    password: str = ""
    code: str = ""

    @validator('phone')
    def check_phone(cls, v):
        if not validate_phone(v):
            raise ValueError('手机号格式不正确')
        return v