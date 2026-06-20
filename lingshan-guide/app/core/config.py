import os

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "your_password"),
    "database": os.getenv("DB_NAME", "scenic_guide_db"),
    "charset": "utf8mb4",
    "autocommit": False,
}

JWT_SECRET = os.getenv("JWT_SECRET", "lingshan_secret_2024")
JWT_EXPIRE_HOURS = 24
DEEPSEEK_KEY = os.getenv("DEEPSEEK_KEY", "")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")
DIFY_DATASET_ID = os.getenv("DIFY_DATASET_ID", "")