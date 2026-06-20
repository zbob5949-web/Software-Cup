#这段代码实现了用户认证和权限管理的核心依赖函数，用于保护API接口和获取当前登录用户信息。
from fastapi import Depends, HTTPException, Header
from database import get_db_connection
from core.security import decode_token, decode_token_payload

#get_db - 数据库连接依赖
def get_db():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    try:
        yield conn
    finally:
        conn.close()

#get_current_user_optional - 可选登录（未登录也能访问）
def get_current_user_optional(authorization: str = Header(None)) -> str | None:
    """获取当前用户手机号，未登录返回None"""
    if not authorization:
        return None
    phone = decode_token(authorization)
    return phone

#get_current_user - 强制登录
def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    phone = decode_token(authorization)
    if not phone:
        raise HTTPException(status_code=401, detail="token无效或过期")
    return phone

#get_current_user_info - 获取完整用户信息
def get_current_user_info(authorization: str = Header(None), db=Depends(get_db)) -> dict:
    """返回当前登录用户的 phone/role，并以数据库中的角色为准。"""
    payload = decode_token_payload(authorization)
    if not payload:
        raise HTTPException(status_code=401, detail="token无效或过期")
    phone = payload.get("sub")
    with db.cursor() as cursor:
        cursor.execute("SELECT phone, role FROM users WHERE phone = %s", (phone,))
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"phone": row["phone"], "role": row.get("role") or "user"}

#get_current_admin_user - 管理员权限
def get_current_admin_user(user: dict = Depends(get_current_user_info)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
