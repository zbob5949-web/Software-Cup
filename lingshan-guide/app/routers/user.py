from fastapi import APIRouter, Depends
from app.dependencies import get_db, get_current_user
from app.services.user_service import send_verification_code, register_user, login_user
from app.models.schemas import GetCodeForm, RegisterForm, LoginForm

router = APIRouter()

@router.post("/api/user/getcode")
def get_code(form: GetCodeForm, db=Depends(get_db)):
    return send_verification_code(db, form.phone, form.code_type)

@router.post("/api/user/register")
def register(form: RegisterForm, db=Depends(get_db)):
    return register_user(db, form.phone, form.code, form.password, form.confirm_password)

@router.post("/api/user/login")
def login(form: LoginForm, db=Depends(get_db)):
    return login_user(db, form.phone, form.password, form.code)

@router.get("/api/user/status")
def status(phone: str = Depends(get_current_user)):
    return {"code": 200, "msg": "success", "data": {"is_login": True, "username": phone}}