import random
import string

def validate_phone(phone: str) -> bool:
    """验证手机号是否为11位数字且以1开头"""
    return phone.isdigit() and len(phone) == 11 and phone.startswith('1')

def validate_password(password: str) -> tuple:
    """验证密码强度，返回 (是否合法, 提示信息)"""
    if len(password) < 6:
        return False, "密码至少6位"
    if len(password) > 20:
        return False, "密码不能超过20位"
    return True, ""

def generate_code() -> str:
    """生成4位随机数字验证码"""
    return ''.join(random.choices(string.digits, k=4))