# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Response
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import pymysql
import os
import uuid
from openai import OpenAI
from datetime import datetime, timedelta
import random
import string
from lingshan_rag import build_rag_prompt, build_route_prompt, retrieve_spot_detail

app = FastAPI(title="灵山景区导览系统", version="1.20")

# ====================== 1. 配置区 ======================
SYSTEM_PROMPT = """你是一个专业的"灵山胜境"景区智能助手，名字叫"小贞"。
你的主要职责是为游客提供关于灵山胜境景区的咨询服务。

【你的知识库】
1. 景区特色：灵山胜境是世界佛教论坛永久会址，拥有88米高的灵山大佛、宏伟的梵宫、九龙灌浴等著名景点。
2. 必看演出：
   - 《九龙灌浴》：通常在上午10:00和下午14:00（具体时间随季节调整），展示太子佛诞生的宏大场景。
   - 《吉祥颂》：在梵宫内演出，讲述释迦牟尼成佛的故事，需凭票或预约观看。
3. 游玩建议：建议游玩时间4-6小时，推荐路线为：灵山大照壁 -> 五智门 -> 九龙灌浴 -> 降魔浮雕 -> 阿育王柱 -> 天下第一掌 -> 灵山大佛（抱佛脚） -> 梵宫。
4. 实用信息：景区开放时间为07:00-17:30（具体以季节为准），门票价格约为210元（仅供参考，以官网为准）。

【回复规则】
1. 语气风格：热情、亲切、充满禅意和礼貌。称呼游客为"您"或"善信"。
2. 处理闲聊：如果游客问你"叫什么"、"你是谁"，请回答："我是灵山景区的智能助手小贞，很高兴为您服务，请问您想了解关于灵山的哪些信息呢？"
3. 拒绝无关：如果游客问与灵山景区无关的问题（如天气、股票、通用百科），请礼貌地拒绝，并引导回景区话题。例如："抱歉，小贞只懂灵山的大小事，关于灵山您有什么想了解的吗？"
4. 格式要求：回答要条理清晰，关键信息（如时间、地点）可以加粗显示。"""

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

# ====================== 2. 数据库配置 ======================
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "@Zjn200627",
    "database": "scenic_guide_db",
    "charset": "utf8mb4",
    "autocommit": False,
}


def get_db_connection():
    """每次请求获取一个新的数据库连接，用完后需手动关闭"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"[数据库] 连接失败: {e}")
        return None


def init_database():
    """服务启动时执行一次，用于建表"""
    conn = get_db_connection()
    if not conn:
        print("[数据库] 初始化失败，请检查 MySQL 是否启动及配置是否正确")
        return

    try:
        with conn.cursor() as cur:
            # 用户表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11) UNIQUE NOT NULL COMMENT '手机号',
                    password VARCHAR(255) NOT NULL COMMENT '密码',
                    role VARCHAR(20) DEFAULT 'user' COMMENT '角色',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
                    last_login TIMESTAMP NULL COMMENT '最后登录时间',
                    INDEX idx_phone (phone)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 验证码表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS verification_sessions (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    phone VARCHAR(11) NOT NULL COMMENT '手机号',
                    code VARCHAR(4) NOT NULL COMMENT '验证码',
                    code_type VARCHAR(20) NOT NULL COMMENT '类型：register/login',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                    expires_at TIMESTAMP NOT NULL COMMENT '过期时间',
                    is_used BOOLEAN DEFAULT FALSE COMMENT '是否已使用',
                    INDEX idx_phone (phone),
                    INDEX idx_expires (expires_at),
                    INDEX idx_type (code_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 聊天记录表
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_records (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    username TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_user_session (username(64), session_id(64), timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

        conn.commit()
        print("[数据库] 初始化完成")
    except Exception as e:
        print(f"[数据库] 建表失败: {e}")
    finally:
        conn.close()


@app.on_event("startup")
def startup_event():
    print("====== 开始初始化数据库 ======")
    init_database()


# ====================== 3. 数据模型定义 ======================
class GetCodeForm(BaseModel):
    phone: str = ""
    code_type: str = "register"


class RegisterForm(BaseModel):
    phone: str = ""
    code: str = ""
    password: str = ""
    confirm_password: str = ""


class ChatForm(BaseModel):
    question: str = ""
    session_id: str = None


def Result(code: int, msg: str, data=None):
    return {"code": code, "msg": msg, "data": data}


# ====================== 4. 工具函数 ======================
def generate_code():
    """生成4位随机数字验证码"""
    return ''.join(random.choices(string.digits, k=4))


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    return phone.isdigit() and len(phone) == 11 and phone[0] == '1'


def validate_password(password: str) -> tuple:
    """验证密码强度"""
    if len(password) < 6:
        return False, "密码长度不能少于6位"
    if len(password) > 20:
        return False, "密码长度不能超过20位"
    return True, ""


# ====================== 5. 核心接口 ======================

# 接口1：获取验证码
@app.post("/api/user/getcode")
def get_verification_code(form: GetCodeForm):
    phone = (form.phone or "").strip()
    code_type = form.code_type or "register"

    if not phone:
        return Result(40031, "请输入手机号")
    if not validate_phone(phone):
        return Result(40031, "手机号格式错误")

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            # 登录验证码：校验手机号是否已注册
            if code_type == "login":
                cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if not cursor.fetchone():
                    return Result(40404, "该手机号未注册")

            # 注册验证码：校验手机号是否已存在
            if code_type == "register":
                cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if cursor.fetchone():
                    return Result(40003, "该手机号已注册")

            # 60秒限制
            one_minute_ago = datetime.now() - timedelta(seconds=60)
            cursor.execute("""
                SELECT COUNT(*) FROM verification_sessions 
                WHERE phone = %s AND code_type = %s AND created_at > %s
            """, (phone, code_type, one_minute_ago))
            if cursor.fetchone()[0] > 0:
                return Result(42901, "60秒倒计时未结束，请稍后重试")

            # 生成并保存验证码
            code = generate_code()
            expires_at = datetime.now() + timedelta(minutes=5)
            cursor.execute("""
                INSERT INTO verification_sessions (phone, code, code_type, expires_at) 
                VALUES (%s, %s, %s, %s)
            """, (phone, code, code_type, expires_at))
            conn.commit()

        print(f"[开发模式] 手机号 {phone} 的 {code_type} 验证码是: {code}")
        return Result(200, "验证码已发送", {"code": code, "phone": phone})

    except Exception as e:
        conn.rollback()
        print(f"[getcode 错误] {e}")
        return Result(50001, "服务器内部错误")
    finally:
        conn.close()


# 接口2：注册
@app.post("/api/user/register")
def register(form: RegisterForm):
    phone = (form.phone or "").strip()
    code = (form.code or "").strip()
    password = (form.password or "").strip()
    confirm_password = (form.confirm_password or "").strip()

    if not phone:
        return Result(40031, "请输入手机号")
    if not validate_phone(phone):
        return Result(40031, "手机号格式错误")
    if not code:
        return Result(40032, "验证码不能为空")
    if not password:
        return Result(40002, "请输入密码")

    is_valid, error_msg = validate_password(password)
    if not is_valid:
        return Result(40005, error_msg)
    if password != confirm_password:
        return Result(40006, "两次输入的密码不一致")

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            # 验证验证码
            cursor.execute("""
                SELECT id, code FROM verification_sessions 
                WHERE phone = %s AND code_type = 'register' AND is_used = FALSE AND expires_at > NOW()
                ORDER BY created_at DESC LIMIT 1
            """, (phone,))
            session = cursor.fetchone()
            if not session or session[1] != code:
                return Result(40033, "验证码错误或已失效")
            session_id_db = session[0]

            # 检查手机号是否已存在
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cursor.fetchone():
                return Result(40003, "该手机号已注册")

            # 创建用户
            cursor.execute(
                "INSERT INTO users (phone, password) VALUES (%s, %s)",
                (phone, password)
            )
            # 标记验证码已使用
            cursor.execute(
                "UPDATE verification_sessions SET is_used = TRUE WHERE id = %s",
                (session_id_db,)
            )
            conn.commit()

        return Result(200, "注册成功！")

    except Exception as e:
        conn.rollback()
        print(f"[register 错误] {e}")
        return Result(50001, "注册失败，请稍后重试")
    finally:
        conn.close()


# 接口3：登录（支持密码和验证码两种方式）
@app.post("/api/user/login")
def login(user_data: dict, response: Response):
    phone = user_data.get("phone", "").strip()
    password = user_data.get("password", "").strip()
    code = user_data.get("code", "").strip()

    if not phone or not validate_phone(phone):
        return Result(40031, "手机号格式错误")

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            # --- 情况 A: 验证码登录 ---
            if code:
                cursor.execute("SELECT id, phone FROM users WHERE phone = %s", (phone,))
                user_result = cursor.fetchone()
                if not user_result:
                    return Result(40404, "该手机号未注册")
                user_id, user_phone = user_result

                cursor.execute("""
                    SELECT id, code FROM verification_sessions 
                    WHERE phone = %s AND code_type = 'login' AND is_used = FALSE AND expires_at > NOW()
                    ORDER BY created_at DESC LIMIT 1
                """, (phone,))
                session = cursor.fetchone()
                if not session or session[1] != code:
                    return Result(40033, "验证码错误或已失效")
                session_id_db = session[0]

                cursor.execute(
                    "UPDATE verification_sessions SET is_used = TRUE WHERE id = %s",
                    (session_id_db,)
                )

            # --- 情况 B: 密码登录 ---
            elif password:
                cursor.execute(
                    "SELECT id, phone, password FROM users WHERE phone = %s",
                    (phone,)
                )
                result = cursor.fetchone()
                if not result or result[2] != password:
                    return Result(40101, "账号或密码错误")
                user_id, user_phone, _ = result

            else:
                return Result(40000, "请求参数错误，请提供密码或验证码")

            # 更新最后登录时间
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            conn.commit()

        # 设置登录 Cookie
        response.set_cookie(key="login_state", value=user_phone, max_age=3600)
        return Result(200, "登录成功", {"username": user_phone})

    except Exception as e:
        conn.rollback()
        print(f"[login 错误] {e}")
        return Result(50001, "登录失败，请稍后重试")
    finally:
        conn.close()


# 接口4：获取用户状态
@app.get("/api/user/status")
async def user_status(request: Request):
    login_state = request.cookies.get("login_state")
    visitor_id = request.cookies.get("visitor_id")

    if login_state:
        return Result(200, "success", {
            "is_login": True,
            "username": login_state,
            "user_id": login_state
        })
    else:
        if not visitor_id:
            visitor_id = f"guest_{int(datetime.timestamp(datetime.now()))}"
        return Result(200, "success", {
            "is_login": False,
            "username": None,
            "user_id": visitor_id
        })


# 接口5：AI 聊天
@app.post("/api/user/chat")
async def chat(form: ChatForm, request: Request, response: Response):
    question = form.question.strip()
    if not question:
        return Result(40004, "请输入问题")

    # --- 身份识别 ---
    login_state = request.cookies.get("login_state")
    visitor_id = request.cookies.get("visitor_id")
    if login_state:
        current_user = login_state
    else:
        current_user = visitor_id or f"guest_{int(datetime.timestamp(datetime.now()))}"
    response.set_cookie(key="visitor_id", value=current_user, max_age=604800)

    # --- 会话管理 ---
    if not form.session_id or form.session_id.lower() == "new":
        session_id = str(uuid.uuid4())
    else:
        session_id = form.session_id

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            # --- 构建历史消息 ---
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            cursor.execute("""
                SELECT role, content FROM chat_records 
                WHERE username = %s AND session_id = %s 
                ORDER BY timestamp ASC
            """, (current_user, session_id))
            for role, content in cursor.fetchall():
                messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": question})

            # --- 调用 AI ---
            my_key = os.environ.get('DEEPSEEK_KEY')
            if not my_key:
                return Result(50003, "服务配置错误：未设置 DEEPSEEK_KEY 环境变量")

            client = OpenAI(api_key=my_key, base_url="https://api.deepseek.com")
            ai_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            answer = ai_response.choices[0].message.content

            # --- 保存记录 ---
            cursor.execute("""
                INSERT INTO chat_records (username, session_id, role, content) 
                VALUES (%s, %s, %s, %s)
            """, (current_user, session_id, "user", question))
            cursor.execute("""
                INSERT INTO chat_records (username, session_id, role, content) 
                VALUES (%s, %s, %s, %s)
            """, (current_user, session_id, "assistant", answer))

            # --- 只保留最近10条 ---
            cursor.execute("""
                DELETE FROM chat_records 
                WHERE username = %s AND session_id = %s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM chat_records 
                        WHERE username = %s AND session_id = %s 
                        ORDER BY timestamp DESC LIMIT 10
                    ) AS tmp
                )
            """, (current_user, session_id, current_user, session_id))

            conn.commit()

        return Result(200, "success", {"answer": answer, "session_id": session_id})

    except Exception as e:
        conn.rollback()
        print(f"[chat 错误] {e}")
        return Result(50002, "AI 处理失败，请稍后重试")
    finally:
        conn.close()


# 接口6：获取历史会话列表
@app.get("/api/user/history")
async def get_history(request: Request):
    login_state = request.cookies.get("login_state")
    visitor_id = request.cookies.get("visitor_id")
    query_user = login_state or visitor_id

    if not query_user:
        return Result(200, "success", {"histories": []})

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT session_id, MIN(timestamp) as first_time 
                FROM chat_records 
                WHERE username = %s 
                GROUP BY session_id 
                ORDER BY first_time DESC
            """, (query_user,))
            sessions = cursor.fetchall()

            histories = []
            for session_id, time in sessions:
                cursor.execute("""
                    SELECT content FROM chat_records 
                    WHERE username = %s AND session_id = %s AND role = 'user' 
                    ORDER BY timestamp ASC LIMIT 1
                """, (query_user, session_id))
                title_row = cursor.fetchone()
                title = (title_row[0][:15] + "...") if title_row else "新对话"
                histories.append({
                    "session_id": session_id,
                    "title": title,
                    "time": str(time)
                })

        return Result(200, "success", {"histories": histories})

    except Exception as e:
        print(f"[history 错误] {e}")
        return Result(50001, "获取历史记录失败")
    finally:
        conn.close()


# ====================== 6. 调试接口 ======================
@app.get("/api/debug/users")
def debug_users():
    conn = get_db_connection()
    if not conn:
        return {"error": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, phone, role, created_at, last_login FROM users")
            rows = cursor.fetchall()
        return {"data": rows}
    finally:
        conn.close()


@app.get("/api/debug/chat")
def debug_chat():
    conn = get_db_connection()
    if not conn:
        return {"error": "数据库连接失败"}
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM chat_records ORDER BY timestamp DESC LIMIT 50")
            rows = cursor.fetchall()
        return {"data": rows}
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
