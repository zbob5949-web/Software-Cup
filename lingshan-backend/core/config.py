#Python后端应用的配置文件，主要用于加载环境变量和设置应用参数
import os
import secrets
from pathlib import Path

# 自动加载项目根目录的 .env 文件，环境变量加载
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

#数据库配置
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "scenic_guide_db"),
    "charset": "utf8mb4",
    "autocommit": False,
}

#应用环境
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
DB_POOL_TIMEOUT = float(os.getenv("DB_POOL_TIMEOUT", "5"))

APP_ENV = os.getenv("APP_ENV", "development").lower()
APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"

#JWT认证，自动生成或读取持久化的JWT密钥
_jwt_secret = os.getenv("JWT_SECRET", "")
if not _jwt_secret or _jwt_secret == "lingshan_secret_2024":
    # 开发环境也尽量保持 token 重启后不失效：优先读取本地持久化密钥。
    # 生产环境仍建议在 .env 中显式配置强随机 JWT_SECRET。
    _secret_file = Path(__file__).resolve().parent.parent / ".jwt_secret"
    try:
        if _secret_file.exists():
            _jwt_secret = _secret_file.read_text(encoding="utf-8").strip()
        if not _jwt_secret:
            _jwt_secret = secrets.token_urlsafe(32)
            _secret_file.write_text(_jwt_secret, encoding="utf-8")
        print("[安全] 未在 .env 中配置强 JWT_SECRET，已使用本地持久化开发密钥；生产环境请设置强随机值")
    except Exception:
        _jwt_secret = secrets.token_urlsafe(32)
        print("[安全] 未配置强 JWT_SECRET，且本地密钥文件不可用；已生成临时开发密钥")
JWT_SECRET = _jwt_secret
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

#跨域配置（CORS）
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "*",
    ).split(",")
    if origin.strip()
]

#业务限制
RETURN_VERIFICATION_CODE = os.getenv("RETURN_VERIFICATION_CODE", "false").lower() == "true"
MAX_AUDIO_UPLOAD_BYTES = int(os.getenv("MAX_AUDIO_UPLOAD_BYTES", str(10 * 1024 * 1024)))
MAX_CHAT_QUESTION_LENGTH = int(os.getenv("MAX_CHAT_QUESTION_LENGTH", "500"))
MAX_FEEDBACK_CONTENT_LENGTH = int(os.getenv("MAX_FEEDBACK_CONTENT_LENGTH", "1000"))

#第三方服务：DeepSeek API密钥（AI对话）；Dify平台配置（API密钥、数据集ID、基础URL）
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")
DIFY_BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1").rstrip("/")

#管理员账户，管理员手机号和密码（可能用于初始账户创建）
ADMIN_PHONE = os.getenv("ADMIN_PHONE", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
