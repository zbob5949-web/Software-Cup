"""
依赖注入模块：数据库连接、用户认证、游客识别
"""

from fastapi import Depends, HTTPException, Header
from app.database import get_db_connection
from app.core.security import get_phone_from_token, identify_user, decode_token


def get_db():
    """数据库连接依赖"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(authorization: str = Header(None)) -> str:
    """
    【必须登录】获取当前正式用户的手机号
    游客或无 token 均返回 401
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录")
    phone = get_phone_from_token(authorization)
    if not phone:
        raise HTTPException(status_code=401, detail="token无效或过期，请重新登录")
    return phone


def get_current_user_optional(authorization: str = Header(None)) -> str | None:
    """
    【可选登录】获取当前用户手机号
    - 已登录用户 → 返回手机号
    - 游客/未登录 → 返回 None
    """
    if not authorization:
        return None
    return get_phone_from_token(authorization)


def get_user_identity(authorization: str = Header(None)) -> dict:
    """
    【身份识别】返回完整身份信息
    返回: {"type": "user"|"guest"|"anonymous", "id": str|None}

    用法:
        identity = Depends(get_user_identity)
        if identity["type"] == "user":
            ...  # 完整功能
        elif identity["type"] == "guest":
            ...  # 游客受限功能
        else:
            ...  # 匿名用户，仅可浏览公开信息
    """
    return identify_user(authorization) if authorization else {"type": "anonymous", "id": None}


def get_guest_or_user(authorization: str = Header(None)) -> dict:
    """
    【游客或正式用户】必须提供有效 token（游客或登录用户均可）
    匿名用户返回 401
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="请先登录或以游客身份访问")
    identity = identify_user(authorization)
    if identity["type"] == "anonymous":
        raise HTTPException(status_code=401, detail="token无效或过期")
    return identity


def get_current_user_info(authorization: str = Header(None), db=Depends(get_db)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    payload = decode_token(authorization)
    if not payload:
        raise HTTPException(status_code=401, detail="token无效或过期")
    phone = payload.get("sub")
    with db.cursor() as cursor:
        cursor.execute("SELECT phone, role FROM users WHERE phone = %s", (phone,))
        row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="用户不存在")
    return {"phone": row["phone"], "role": row.get("role") or "user"}


def get_current_admin_user(user: dict = Depends(get_current_user_info)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
