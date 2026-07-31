from datetime import date, datetime

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.utils.response import Result

router = APIRouter()


def _date_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value) if value is not None else None


@router.get('/api/admin/conversations')
def list_conversations(
    keyword: str | None = Query(None, max_length=80),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    """列出用户会话摘要，供管理员查看游客端实际对话记录。"""
    where = ''
    params: list[object] = []
    if keyword and keyword.strip():
        where = 'WHERE (phone LIKE %s OR session_id LIKE %s)'
        value = f'%{keyword.strip()}%'
        params.extend([value, value])

    with db.cursor() as cursor:
        cursor.execute(f'SELECT COUNT(DISTINCT session_id) AS total FROM chat_records {where}', tuple(params))
        total_row = cursor.fetchone() or {}
        cursor.execute(
            f'''
            SELECT session_id,
                   MAX(phone) AS phone,
                   COUNT(*) AS message_count,
                   MIN(created_at) AS created_at,
                   MAX(created_at) AS last_message_at
            FROM chat_records
            {where}
            GROUP BY session_id
            ORDER BY last_message_at DESC
            LIMIT %s OFFSET %s
            ''',
            tuple(params + [limit, offset]),
        )
        rows = cursor.fetchall()
        sessions = []
        for row in rows:
            session_id = row['session_id']
            cursor.execute(
                "SELECT content FROM chat_records WHERE session_id = %s AND role = 'user' ORDER BY id ASC LIMIT 1",
                (session_id,),
            )
            first = cursor.fetchone()
            cursor.execute(
                'SELECT content FROM chat_records WHERE session_id = %s ORDER BY id DESC LIMIT 1',
                (session_id,),
            )
            last = cursor.fetchone()
            title = (first or {}).get('content') or '新对话'
            preview = (last or {}).get('content') or title
            sessions.append({
                'session_id': session_id,
                'phone': row.get('phone') or '游客',
                'title': title[:80],
                'preview': preview[:160],
                'message_count': int(row.get('message_count') or 0),
                'created_at': _date_value(row.get('created_at')),
                'last_message_at': _date_value(row.get('last_message_at')),
            })

    return ok({'sessions': sessions, 'total': int(total_row.get('total') or 0), 'limit': limit, 'offset': offset})


@router.get('/api/admin/conversations/{session_id}')
def conversation_detail(
    session_id: str,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        cursor.execute(
            'SELECT id, phone, role, content, source, created_at FROM chat_records WHERE session_id = %s ORDER BY id ASC',
            (session_id,),
        )
        rows = cursor.fetchall()
    if not rows:
        return Result(404, '会话不存在')
    messages = [{
        'id': row.get('id'),
        'phone': row.get('phone') or '游客',
        'role': row.get('role'),
        'content': row.get('content') or '',
        'source': row.get('source'),
        'created_at': _date_value(row.get('created_at')),
    } for row in rows]
    return ok({'session_id': session_id, 'messages': messages})


@router.delete('/api/admin/conversations/{session_id}')
def delete_conversation(
    session_id: str,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        with db.cursor() as cursor:
            cursor.execute('DELETE FROM chat_records WHERE session_id = %s', (session_id,))
            deleted = cursor.rowcount
        db.commit()
        if not deleted:
            return Result(404, '会话不存在')
        return ok({'session_id': session_id}, '会话已删除')
    except Exception as exc:
        db.rollback()
        return Result(500, f'删除会话失败：{exc}')