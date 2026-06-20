# app/services/user_service.py

from datetime import datetime, timedelta
import bcrypt

from core.config import RETURN_VERIFICATION_CODE
from validators import validate_phone, validate_password, generate_code

_failed_login_attempts: dict[str, tuple[int, datetime]] = {}
MAX_LOGIN_FAILURES = 5
LOGIN_LOCK_SECONDS = 10 * 60


def _is_login_locked(phone: str) -> bool:
    attempts, locked_until = _failed_login_attempts.get(phone, (0, datetime.min))
    return attempts >= MAX_LOGIN_FAILURES and datetime.now() < locked_until


def _record_login_failure(phone: str):
    attempts, locked_until = _failed_login_attempts.get(phone, (0, datetime.min))
    if datetime.now() >= locked_until:
        attempts = 0
    attempts += 1
    _failed_login_attempts[phone] = (attempts, datetime.now() + timedelta(seconds=LOGIN_LOCK_SECONDS))


def _clear_login_failures(phone: str):
    _failed_login_attempts.pop(phone, None)


def send_verification_code(conn, phone: str, code_type: str):
    """
    发送验证码
    - 检查手机号格式
    - 检查60秒内是否重复发送
    - 检查注册/登录场景下的用户状态
    - 生成6位验证码存入 verification_sessions
    """
    if not validate_phone(phone):
        return {"code": 40031, "msg": "手机号格式错误", "data": None}
    if _is_login_locked(phone):
        return {"code": 42902, "msg": "登录失败次数过多，请稍后再试", "data": None}

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

        data = {"phone": phone}
        if RETURN_VERIFICATION_CODE:
            print(f"[开发模式] 手机号 {phone} 的 {code_type} 验证码是: {code}")
            data["code"] = code
        return {"code": 200, "msg": "验证码已发送", "data": data}

    except Exception as e:
        conn.rollback()
        print(f"[send_code 错误] {e}")
        return {"code": 50001, "msg": "服务器内部错误", "data": None}


def register_user(conn, phone: str, code: str, password: str, confirm_password: str):
    """
    用户注册
    - 校验手机号、验证码、密码强度、两次密码
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

            # 创建用户（密码 bcrypt 哈希）
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            cursor.execute(
                "INSERT INTO users (phone, password) VALUES (%s, %s)",
                (phone, hashed.decode("utf-8"))
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
    返回 token 和用户信息
    """
    if not validate_phone(phone):
        return {"code": 40031, "msg": "手机号格式错误", "data": None}
    if _is_login_locked(phone):
        return {"code": 42902, "msg": "登录失败次数过多，请稍后再试", "data": None}

    try:
        with conn.cursor() as cursor:
            # 先确定用户存在
            cursor.execute("SELECT id, phone, password, role FROM users WHERE phone = %s", (phone,))
            user_row = cursor.fetchone()
            if not user_row:
                return {"code": 40404, "msg": "该手机号未注册", "data": None}
            user_id = user_row["id"]
            phone = user_row["phone"]
            db_password = user_row["password"]
            role = user_row.get("role") or "user"

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
                    _record_login_failure(phone)
                    return {"code": 40033, "msg": "验证码错误或已失效", "data": None}
                # 标记验证码已使用
                cursor.execute(
                    "UPDATE verification_sessions SET is_used = TRUE WHERE id = %s",
                    (code_session["id"],)
                )
            # 密码登录
            elif password:
                if not bcrypt.checkpw(password.encode("utf-8"), db_password.encode("utf-8")):
                    _record_login_failure(phone)
                    return {"code": 40101, "msg": "账号或密码错误", "data": None}
            else:
                return {"code": 40000, "msg": "请求参数错误，请提供密码或验证码", "data": None}

            # 更新最后登录时间
            cursor.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))
            conn.commit()
            _clear_login_failures(phone)

        # 生成 token（简单的UUID，生产环境建议 JWT）
        from core.security import create_token
        token = create_token(phone, role)
        return {"code": 200, "msg": "登录成功", "data": {"token": token, "phone": phone, "role": role}}

    except Exception as e:
        conn.rollback()
        print(f"[login 错误] {e}")
        return {"code": 50001, "msg": "登录失败，请稍后重试", "data": None}
