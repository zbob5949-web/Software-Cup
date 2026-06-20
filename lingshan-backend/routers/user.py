# ==================== 用户模块 ====================
# 接口01-04：验证码/注册/登录/状态检查
from fastapi import APIRouter, Depends
from dependencies import get_db, get_current_user, get_current_user_info
from services.user_service import send_verification_code, register_user, login_user
from models.schemas import GetCodeForm, RegisterForm, LoginForm

router = APIRouter()

# ===== 接口01：发送验证码 =====
# 注意：同一手机号60秒内不能重复发送
@router.post("/api/user/getcode")
def get_code(form: GetCodeForm, db=Depends(get_db)):
    return send_verification_code(db, form.phone, form.code_type)

# ===== 接口02：用户注册 =====
# 注意：密码≥6位≤20位，需与验证码接口配合使用
@router.post("/api/user/register")
def register(form: RegisterForm, db=Depends(get_db)):
    return register_user(db, form.phone, form.code, form.password, form.confirm_password)

# ===== 接口03：用户登录 =====
# 说明：支持密码登录(传password)或验证码登录(传code)，二选一
# 前端收到token后需存储，后续请求Header加 Authorization: Bearer <token>
@router.post("/api/user/login")
def login(form: LoginForm, db=Depends(get_db)):
    return login_user(db, form.phone, form.password, form.code)

# ===== 接口04：登录状态检查 =====
# 说明：用于前端判断用户是否已登录、token是否过期
@router.get("/api/user/status")
def status(user: dict = Depends(get_current_user_info)):
    return {"code": 200, "msg": "success", "data": {"is_login": True, "username": user["phone"], "phone": user["phone"], "role": user["role"]}}
