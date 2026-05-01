# -*- coding: utf-8 -*-
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import sqlite3

app = FastAPI()

SAFE_API_KEY = "software-cup-2026-secret"

# 1️⃣ 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2️⃣ 连接数据库（会自动创建一个.db文件）
conn = sqlite3.connect("user1.db", check_same_thread=False)
cursor = conn.cursor()

# 3️⃣ 创建表（如果不存在）
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY NOT NULL,
    password TEXT NOT NULL
)
""")
conn.commit()

# 4️⃣ 请求体
# 前端传过来的数据的格式
class User(BaseModel):
    username: str = ""
    password: str = ""
    api_key: str = ""

# 5️⃣ 统一返回
def Result(code: int, msg: str, data=None):
    return {
        "code": code,
        "msg": msg,
        "data": data
    }

# ======================
# 注册
# ======================
@app.post("/api/user/register")
def register(user: User):
    username = (user.username or "").strip()
    password = (user.password or "").strip()

    if user.api_key != SAFE_API_KEY:
        return Result(40004, "访问受限：API-Key 错误")

    if not username:
        return Result(40001, "用户名不能为空")
    if not password:
        return Result(40002, "密码不能为空")

    # 查询是否存在
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    if cursor.fetchone():
        return Result(40003, "用户名已存在")

    # 插入
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
        conn.commit()
        return Result(200, "注册成功")
    except Exception as e:
        return Result(50001, f"注册失败: {str(e)}")

# ======================
# 启动
# ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)