from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import ok
from app.utils.response import Result

router = APIRouter()


def serialize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def order_row(row):
    return {key: serialize(row.get(key)) for key in (
        'id', 'order_no', 'user_id', 'phone', 'ticket_id', 'ticket_name', 'ticket_type',
        'quantity', 'unit_price', 'total_amount', 'visitor_name', 'visitor_phone',
        'order_status', 'remark', 'created_at', 'updated_at',
    )}


@router.get('/api/admin/orders')
def list_orders(
    keyword: str | None = Query(None, max_length=80),
    status: str | None = Query(None, max_length=20),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    where = ['1=1']
    params: list[object] = []
    if keyword and keyword.strip():
        value = f'%{keyword.strip()}%'
        where.append('(o.order_no LIKE %s OR u.phone LIKE %s OR o.visitor_name LIKE %s OR o.visitor_phone LIKE %s)')
        params.extend([value, value, value, value])
    if status:
        where.append('o.order_status = %s')
        params.append(status)
    with db.cursor() as cursor:
        cursor.execute(f'''SELECT o.*, u.phone, t.name AS ticket_name, t.ticket_type
                           FROM ticket_orders o JOIN users u ON u.id = o.user_id
                           JOIN tickets t ON t.id = o.ticket_id
                           WHERE {' AND '.join(where)} ORDER BY o.created_at DESC''', tuple(params))
        items = [order_row(row) for row in cursor.fetchall()]
    return ok({'orders': items, 'total': len(items)})


@router.get('/api/admin/orders/{order_no}')
def order_detail(order_no: str, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('''SELECT o.*, u.phone, t.name AS ticket_name, t.ticket_type
                         FROM ticket_orders o JOIN users u ON u.id = o.user_id
                         JOIN tickets t ON t.id = o.ticket_id
                         WHERE o.order_no = %s''', (order_no,))
        row = cursor.fetchone()
    if not row:
        return Result(404, '订单不存在')
    return ok({'order': order_row(row)})


@router.put('/api/admin/orders/{order_no}/status')
def update_order_status(order_no: str, payload: dict, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    next_status = str(payload.get('order_status') or '').strip()
    allowed = {'pending', 'paid', 'cancelled', 'completed', 'refunded'}
    if next_status not in allowed:
        return Result(400, '订单状态无效')
    try:
        with db.cursor() as cursor:
            cursor.execute('UPDATE ticket_orders SET order_status = %s WHERE order_no = %s', (next_status, order_no))
            if cursor.rowcount == 0:
                return Result(404, '订单不存在')
        db.commit()
        return ok({'order_no': order_no, 'order_status': next_status}, '订单状态更新成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'订单状态更新失败：{exc}')