"""
用户路由：注册、登录、游客模式、token 刷新、状态查询
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.dependencies import get_db, get_current_user, get_user_identity
from app.services.user_service import send_verification_code, register_user, login_user, create_guest_session
from app.models.schemas import GetCodeForm, RegisterForm, LoginForm
from app.core.security import refresh_access_token
from app.utils.response import Result

router = APIRouter()

# ====================== 注册 & 登录 ======================

@router.post("/api/user/getcode")
def get_code(form: GetCodeForm, db=Depends(get_db)):
    return send_verification_code(db, form.phone, form.code_type)


@router.post("/api/user/register")
def register(form: RegisterForm, db=Depends(get_db)):
    return register_user(db, form.phone, form.code, form.password, form.confirm_password)


@router.post("/api/user/login")
def login(form: LoginForm, db=Depends(get_db)):
    return login_user(db, form.phone, form.password, form.code)


# ====================== 游客模式 ======================

@router.post("/api/user/guest")
def login_as_guest():
    """
    游客模式登录
    无需手机号注册，直接获取游客 token
    返回的 token 可用于基础功能（景点、路线、FAQ、天气、有限次AI对话）
    不可使用：收藏、历史记录查询
    """
    return create_guest_session()


# ====================== Token 刷新 ======================

class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/api/user/refresh")
def refresh_token(req: RefreshRequest):
    """
    使用 refresh_token 换取新的 access_token
    避免频繁重新登录
    """
    new_token = refresh_access_token(req.refresh_token)
    if not new_token:
        return Result(40101, "refresh_token无效或已过期")
    return Result(200, "token刷新成功", {"token": new_token})


# ====================== 用户状态 ======================

@router.get("/api/user/status")
def status(phone: str = Depends(get_current_user)):
    """查询已登录用户状态"""
    return {"code": 200, "msg": "success", "data": {"is_login": True, "username": phone, "type": "user"}}


@router.get("/api/user/identity")
def identity(identity: dict = Depends(get_user_identity)):
    """
    查询当前身份（游客/用户/未登录）
    返回: {"type": "user"|"guest"|"anonymous", "id": "手机号"|"guest_xxx"|null}
    """
    return {
        "code": 200,
        "msg": "success",
        "data": {
            "type": identity["type"],
            "id": identity["id"],
        }
    }
