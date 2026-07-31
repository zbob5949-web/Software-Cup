from fastapi import APIRouter, Depends
from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.utils.response import Result

router = APIRouter()

@router.get('/api/admin/users')
def list_users(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('''SELECT id, phone, role, is_active, is_super_admin, created_at, last_login, last_login_ip FROM users ORDER BY created_at DESC''')
        users = [{**row, 'is_active': bool(row.get('is_active')), 'is_super_admin': bool(row.get('is_super_admin')), 'created_at': str(row.get('created_at')) if row.get('created_at') else None, 'last_login': str(row.get('last_login')) if row.get('last_login') else None, 'last_login_ip': row.get('last_login_ip')} for row in cursor.fetchall()]
    return ok({'users': users})

@router.put('/api/admin/users/{user_id}')
def update_user(user_id: int, payload: dict, current: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    fields, params = [], []
    if 'is_active' in payload: fields.append('is_active = %s'); params.append(bool(payload['is_active']))
    if 'role' in payload:
        if not current.get('is_super_admin'): return Result(403, '只有超级管理员可以修改角色')
        if payload['role'] not in ('user', 'admin'): return Result(400, '角色无效')
        fields.append('role = %s'); params.append(payload['role'])
    if 'is_super_admin' in payload:
        if not current.get('is_super_admin'): return Result(403, '只有超级管理员可以修改超级管理员状态')
        fields.append('is_super_admin = %s'); params.append(bool(payload['is_super_admin']))
    if not fields: return Result(400, '没有需要更新的字段')
    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT phone, is_super_admin FROM users WHERE id = %s', (user_id,))
            row = cursor.fetchone()
            if not row: return Result(404, '用户不存在')

            # 🔒 admin 账号保护：不可降级、不可取消超级管理员、不可停用
            if row['phone'] == 'admin':
                if 'role' in payload and payload['role'] != 'admin':
                    return Result(403, 'admin 是系统主管理员，不可降级为普通用户')
                if 'is_super_admin' in payload and not payload['is_super_admin']:
                    return Result(403, 'admin 是系统主管理员，不可取消超级管理员权限')
                if 'is_active' in payload and not payload['is_active']:
                    return Result(403, 'admin 是系统主管理员，不可被停用')

            if row['phone'] == current['phone'] and ('is_active' in payload and not payload['is_active']): return Result(400, '不能停用当前登录账号')
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = %s", params + [user_id])
        db.commit()
        return ok({'id': user_id}, '用户状态更新成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'用户状态更新失败：{exc}')
