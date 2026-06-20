# app/services/user_service.py

from datetime import datetime, timedelta

from app.validators import validate_phone, validate_password, generate_code
from app.core.security import (
    hash_password,
    verify_password,
    create_token,
    create_refresh_token,
    create_guest_token,
)


def send_verification_code(conn, phone: str, code_type: str):
    """
    发送验证码
    - 检查手机号格式
    - 检查60秒内是否重复发送
    - 检查注册/登录场景下的用户状态
    - 生成4位验证码存入 verification_sessions
    """
    if not validate_phone(phone):
        return {"code": 40031, "msg": "手机号格式错误", "data": None}

    try:
        with conn.cursor() as cursor:
            # 注册场景：手机号不能已存在
            if code_type == "register":
                cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if cursor.fetchone():
                    return {"code": 40003, "msg": "该手机号已注册", "data": None}
            # 登录场景：手机号必须已注册
            elif code_type == "login":
                cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
                if not cursor.fetchone():
                    return {"code": 40404, "msg": "该手机号未注册", "data": None}

            # 60秒限制
            one_minute_ago = datetime.now() - timedelta(seconds=60)
            cursor.execute(
                """SELECT COUNT(*) FROM verification_sessions
                   WHERE phone = %s AND code_type = %s AND created_at > %s""",
                (phone, code_type, one_minute_ago)
            )
            row = cursor.fetchone()
            if row["COUNT(*)"] > 0:
                return {"code": 42901, "msg": "60秒倒计时未结束，请稍后重试", "data": None}

            # 生成验证码
            code = generate_code()
            expires_at = datetime.now() + timedelta(minutes=5)
            cursor.execute(
                """INSERT INTO verification_sessions (phone, code, code_type, expires_at)
                   VALUES (%s, %s, %s, %s)""",
                (phone, code, code_type, expires_at)
            )
            conn.commit()

        print(f"[开发模式] 手机号 {phone} 的 {code_type} 验证码是: {code}")
        return {"code": 200, "msg": "验证码已发送", "data": {"code": code, "phone": phone}}

    except Exception as e:
        conn.rollback()
        print(f"[send_code 错误] {e}")
        return {"code": 50001, "msg": "服务器内部错误", "data": None}


def _is_bcrypt_hash(password_hash: str) -> bool:
    """判断密码是否已经是 bcrypt 哈希"""
    return password_hash.startswith("$2b$") or password_hash.startswith("$2a$")


def register_user(conn, phone: str, code: str, password: str, confirm_password: str):
    """
    用户注册
    - 校验手机号、验证码、密码强度、两次密码
    - 使用 bcrypt 哈希存储密码
    - 创建用户并标记验证码已使用
    """
    if not validate_phone(phone):
        return {"code": 40031, "msg": "手机号格式错误", "data": None}
    if not code:
        return {"code": 40032, "msg": "验证码不能为空", "data": None}
    if not password:
        return {"code": 40002, "msg": "请输入密码", "data": None}
    is_valid, msg = validate_password(password)
    if not is_valid:
        return {"code": 40005, "msg": msg, "data": None}
    if password != confirm_password:
        return {"code": 40006, "msg": "两次输入的密码不一致", "data": None}

    try:
        with conn.cursor() as cursor:
            # 验证验证码
            cursor.execute(
                """SELECT id, code FROM verification_sessions
                   WHERE phone = %s AND code_type = 'register'
                   AND is_used = FALSE AND expires_at > NOW()
                   ORDER BY created_at DESC LIMIT 1""",
                (phone,)
            )
            session = cursor.fetchone()
            if not session or session["code"] != code:
                return {"code": 40033, "msg": "验证码错误或已失效", "data": None}
            session_id_db = session["id"]

            # 再次检查手机号是否已注册
            cursor.execute("SELECT id FROM users WHERE phone = %s", (phone,))
            if cursor.fetchone():
                return {"code": 40003, "msg": "该手机号已注册", "data": None}

            # 创建用户（bcrypt 哈希存储密码）
            hashed = hash_password(password)
            cursor.execute(
                "INSERT INTO users (phone, password) VALUES (%s, %s)",
                (phone, hashed)
            )
            # 标记验证码已使用
            cursor.execute(
                "UPDATE verification_sessions SET is_used = TRUE WHERE id = %s",
                (session_id_db,)
            )
            conn.commit()
        return {"code": 200, "msg": "注册成功！", "data": None}

    except Exception as e:
        conn.rollback()
        print(f"[register 错误] {e}")
        return {"code": 50001, "msg": "注册失败，请稍后重试", "data": None}


def login_user(conn, phone: str, password: str, code: str):
    """
    用户登录 (密码登录 or 验证码登录)
    返回 JWT access token + refresh token 和用户信息
    """
    if not validate_phone(phone):
        return {"code": 40031, "msg": "手机号格式错误", "data": None}

    try:
        with conn.cursor() as cursor:
            # 先确定用户存在
            cursor.execute("SELECT id, phone, password FROM users WHERE phone = %s", (phone,))
            user_row = cursor.fetchone()
            if not user_row:
                return {"code": 40404, "msg": "该手机号未注册", "data": None}
            user_id = user_row["id"]
            phone = user_row["phone"]
            db_password = user_row["password"]

            # 验证码登录
            if code:
                cursor.execute(
                    """SELECT id, code FROM verification_sessions
                       WHERE phone = %s AND code_type = 'login'
                       AND is_used = FALSE AND expires_at > NOW()
                       ORDER BY created_at DESC LIMIT 1""",
                    (phone,)
                )
                code_session = cursor.fetchone()
                if not code_session or code_session["code"] != code:
                    return {"code": 40033, "msg": "验证码错误或已失效", "data": None}
                # 标记验证码已使用
                cursor.execute(
                    "UPDATE verification_sessions SET is_used = TRUE WHERE id = %s",
                    (code_session["id"],)
                )
            # 密码登录
            elif password:
                # 兼容旧数据：如果密码不是 bcrypt 格式，直接比对后再自动升级
                if _is_bcrypt_hash(db_password):
                    if not verify_password(password, db_password):
                        return {"code": 40101, "msg": "账号或密码错误", "data": None}
                else:
                    # 旧版明文密码兼容
                    if password != db_password:
                        return {"code": 40101, "msg": "账号或密码错误", "data": None}
                    # 自动升级为 bcrypt 哈希
                    hashed = hash_password(password)
                    cursor.execute(
                        "UPDATE users SET password = %s WHERE id = %s",
                        (hashed, user_id)
                    )
            else:
                return {"code": 40000, "msg": "请求参数错误，请提供密码或验证码", "data": None}

            # 更新最后登录时间
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            conn.commit()

        # 生成 JWT token
        access_token = create_token(phone)
        refresh_token = create_refresh_token(phone)
        return {
            "code": 200,
            "msg": "登录成功",
            "data": {
                "token": access_token,
                "refresh_token": refresh_token,
                "phone": phone,
            }
        }

    except Exception as e:
        conn.rollback()
        print(f"[login 错误] {e}")
        return {"code": 50001, "msg": "登录失败，请稍后重试", "data": None}


def create_guest_session():
    """
    创建游客会话
    无需注册，直接返回游客 token 和 guest_id
    """
    token, guest_id = create_guest_token()
    return {
        "code": 200,
        "msg": "游客模式已启用（部分功能受限）",
        "data": {
            "token": token,
            "guest_id": guest_id,
            "type": "guest",
            "limits": {
                "daily_chat": 10,           # 每日AI对话次数
                "can_favorite": False,      # 不可收藏
                "can_view_history": False,  # 不可查看历史
                "description": "游客模式下可使用基础导览、景点查询、天气查询、FAQ匹配和有限次数的AI对话",
            }
        }
    }
