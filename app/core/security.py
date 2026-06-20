# app/core/security.py
"""
安全模块：JWT 令牌管理、密码哈希、游客支持
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import bcrypt

from app.core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    GUEST_TOKEN_EXPIRE_HOURS,
)

# ====================== 密码工具 ======================

def hash_password(password: str) -> str:
    """使用 bcrypt 对密码进行哈希"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希值是否匹配"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# ====================== JWT 令牌工具 ======================

def _create_jwt(payload: dict, expire_hours: int) -> str:
    """内部方法：生成 JWT 令牌（使用 UTC 时间）"""
    now = datetime.now(timezone.utc)
    payload.update({
        "iat": now,
        "exp": now + timedelta(hours=expire_hours),
        "jti": uuid.uuid4().hex[:12],  # 唯一令牌ID
    })
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_token(phone: str, expires_in: int | None = None) -> str:
    """
    为已登录用户生成 access token
    """
    hours = expires_in // 3600 if expires_in else JWT_EXPIRE_HOURS
    return _create_jwt({
        "sub": phone,           # subject = 手机号
        "type": "access",
        "role": "user",
    }, expire_hours=hours)


def create_refresh_token(phone: str) -> str:
    """
    生成 refresh token（有效期更长，用于续期）
    """
    expire_days = REFRESH_TOKEN_EXPIRE_DAYS
    now = datetime.now(timezone.utc)
    payload = {
        "sub": phone,
        "type": "refresh",
        "role": "user",
        "iat": now,
        "exp": now + timedelta(days=expire_days),
        "jti": uuid.uuid4().hex[:12],
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_guest_token() -> tuple[str, str]:
    """
    为游客生成来宾令牌
    返回 (token, guest_id)
    """
    guest_id = f"guest_{uuid.uuid4().hex[:12]}"
    token = _create_jwt({
        "sub": guest_id,
        "type": "guest",
        "role": "guest",
    }, expire_hours=GUEST_TOKEN_EXPIRE_HOURS)
    return token, guest_id


def refresh_access_token(refresh_token: str) -> str | None:
    """
    使用 refresh token 换取新的 access token
    返回新的 access token，失败返回 None
    """
    try:
        payload = jwt.decode(
            refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            leeway=_JWT_LEEWAY
        )
        if payload.get("type") != "refresh":
            return None
        phone = payload.get("sub")
        if not phone:
            return None
        return create_token(phone)
    except jwt.PyJWTError:
        return None

# ====================== JWT 解码 ======================

_JWT_LEEWAY = 10  # 10秒时钟偏差容忍

def decode_token(authorization: str) -> dict | None:
    """
    从 Authorization header 中解析 JWT，返回完整的 payload
    header 格式: Bearer <token>

    返回 dict 包含: sub, type, role, exp, iat, jti
    失败或过期返回 None
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:].strip()
    try:
        payload = jwt.decode(
            token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
            leeway=_JWT_LEEWAY
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def get_phone_from_token(authorization: str) -> str | None:
    """
    从 Authorization header 获取已登录用户的手机号
    仅返回正式用户（role=user）的手机号，游客返回 None
    """
    payload = decode_token(authorization)
    if not payload:
        return None
    if payload.get("type") != "access" or payload.get("role") != "user":
        return None
    return payload.get("sub")


def get_guest_id_from_token(authorization: str) -> str | None:
    """
    从 Authorization header 获取游客 ID
    仅返回游客（role=guest）的 ID，正式用户返回 None
    """
    payload = decode_token(authorization)
    if not payload:
        return None
    if payload.get("role") != "guest":
        return None
    return payload.get("sub")


def identify_user(authorization: str) -> dict:
    """
    从 Authorization header 识别用户身份
    返回 {"type": "user"|"guest"|"anonymous", "id": str|None}
    """
    payload = decode_token(authorization)
    if not payload:
        return {"type": "anonymous", "id": None}

    role = payload.get("role", "anonymous")
    sub = payload.get("sub")
    token_type = payload.get("type", "")

    if role == "user" and token_type == "access":
        return {"type": "user", "id": sub}
    elif role == "guest":
        return {"type": "guest", "id": sub}

    return {"type": "anonymous", "id": None}


# ====================== 兼容旧接口（内存存储已废弃） ======================

# 保留旧接口签名兼容，但内部改用 JWT
def create_token_compat(phone: str, expires_in: int = 3600) -> str:
    """【已废弃】兼容旧代码，请使用 create_token"""
    return create_token(phone, expires_in)
