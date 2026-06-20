import os


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip('"').strip("'")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "your_password"),
    "database": os.getenv("DB_NAME", "scenic_guide_db"),
    "charset": "utf8mb4",
    "autocommit": False,
}

JWT_SECRET = os.getenv("JWT_SECRET", "lingshan_secret_key_2024_please_change_in_production_32chars")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 7
GUEST_TOKEN_EXPIRE_HOURS = 12
# 游客每日对话配额
GUEST_DAILY_CHAT_LIMIT = 10
DEEPSEEK_KEY = _env("DEEPSEEK_KEY")
DIFY_API_KEY = _env("DIFY_API_KEY")
DIFY_DATASET_ID = _env("DIFY_DATASET_ID")
DIFY_API_BASE_URL = _env("DIFY_API_BASE_URL", "http://localhost:8080").rstrip("/")
