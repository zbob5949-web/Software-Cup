from fastapi import Depends, HTTPException, Header
from app.database import get_db_connection
from app.core.security import decode_token

def get_db():
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    try:
        yield conn
    finally:
        conn.close()
def get_current_user_optional(authorization: str = Header(None)) -> str | None:
    """获取当前用户手机号，未登录返回None"""
    if not authorization:
        return None
    phone = decode_token(authorization)
    return phone
def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="未登录")
    phone = decode_token(authorization)
    if not phone:
        raise HTTPException(status_code=401, detail="token无效或过期")
    return phone