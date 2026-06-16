#轻量级JWT（JSON Web Token）的生成和验证系统
import base64
import hashlib
import hmac
import json
import secrets
import time
from core.config import JWT_EXPIRE_HOURS, JWT_SECRET


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _sign(message: str) -> str:
    digest = hmac.new(JWT_SECRET.encode("utf-8"), message.encode("ascii"), hashlib.sha256).digest()
    return _b64encode(digest)

#Token生成 (create_token)
def create_token(phone: str, role: str = "user", expires_in: int | None = None) -> str:
    """生成带 HMAC 签名和过期时间的轻量 token。"""
    now = int(time.time())
    ttl = expires_in if expires_in is not None else JWT_EXPIRE_HOURS * 3600
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": phone,
        "role": role or "user",
        "iat": now,
        "exp": now + ttl,
        "jti": secrets.token_urlsafe(12),
    }
    head = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{head}.{body}"
    return f"{signing_input}.{_sign(signing_input)}"

#Token验证 (decode_token_payload)
def decode_token_payload(authorization: str) -> dict | None:
    """解析 Authorization header，返回 token payload。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    try:
        head, body, signature = token.split(".")
        signing_input = f"{head}.{body}"
        if not hmac.compare_digest(_sign(signing_input), signature):
            return None
        payload = json.loads(_b64decode(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        phone = payload.get("sub")
        if not isinstance(phone, str) or not phone:
            return None
        return payload
    except Exception:
        return None

#便捷的手机号提取 (decode_token)
def decode_token(authorization: str) -> str | None:
    """
    从 Authorization header 中解析用户手机号
    header 格式: Bearer <token>
    """
    payload = decode_token_payload(authorization)
    return payload.get("sub") if payload else None
