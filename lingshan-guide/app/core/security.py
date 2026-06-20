# app/core/security.py

import uuid
import base64
from datetime import datetime, timedelta

# 简单 token 存储：{token: (phone, expire_time)}，生产请用 JWT 或 Redis
_token_store: dict[str, tuple[str, datetime]] = {}

def create_token(phone: str, expires_in: int = 3600) -> str:
    """生成 token，有效期默认 1 小时"""
    token = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode()
    expire = datetime.now() + timedelta(seconds=expires_in)
    _token_store[token] = (phone, expire)
    return token

def decode_token(authorization: str) -> str | None:
    """
    从 Authorization header 中解析用户手机号
    header 格式: Bearer <token>
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    info = _token_store.get(token)
    if not info:
        return None
    phone, expire = info
    if datetime.now() > expire:
        del _token_store[token]
        return None
    return phone