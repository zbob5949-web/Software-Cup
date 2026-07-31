from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends

from app.dependencies import get_db, get_user_identity
from app.utils.response import Result

router = APIRouter()


def serialize(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def require_formal_user(identity: dict = Depends(get_user_identity)) -> dict:
    if identity.get('type') == 'guest':
        raise Exception('游客模式不能创建或查看订单，请注册或登录')
    if identity.get('type') != 'user':
        raise Exception('请先登录')
    return identity


def order_payload(row):
    return {key: serialize(row.get(key)) for key in (
        'id', 'order_no', 'user_id', 'ticket_id', 'ticket_name', 'ticket_type', 'quantity',
        'unit_price', 'total_amount', 'visitor_name', 'visitor_phone', 'order_status',
        'remark', 'created_at', 'updated_at',
    )}


@router.post('/api/orders')
def create_order(payload: dict, identity: dict = Depends(get_user_identity), db=Depends(get_db)):
    if identity.get('type') == 'guest':
        return Result(403, '游客模式不能创建订单，请注册或登录')
    if identity.get('type') != 'user':
        return Result(401, '请先登录')
    try:
        ticket_id = int(payload.get('ticket_id'))
        quantity = max(1, min(int(payload.get('quantity') or 1), 20))
    except (TypeError, ValueError):
        return Result(400, '票种或数量无效')
    visitor_name = str(payload.get('visitor_name') or '').strip()
    visitor_phone = str(payload.get('visitor_phone') or identity.get('id') or '').strip()
    if not visitor_name or not visitor_phone:
        return Result(400, '请填写游客姓名和手机号')
    pay_direct = bool(payload.get('pay_direct'))

    try:
        with db.cursor() as cursor:
            cursor.execute('SELECT id, name, ticket_type, price, stock, status FROM tickets WHERE id = %s FOR UPDATE', (ticket_id,))
            ticket = cursor.fetchone()
            if not ticket or ticket.get('status') != 'on_sale':
                return Result(404, '票种不存在或已停售')
            if int(ticket.get('stock') or 0) < quantity:
                return Result(409, '票种库存不足')
            cursor.execute('SELECT id FROM users WHERE phone = %s', (identity.get('id'),))
            user = cursor.fetchone()
            if not user:
                return Result(401, '用户不存在，请重新登录')
            order_no = f"LS{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid4().hex[:6].upper()}"
            unit_price = ticket['price']
            total_amount = unit_price * quantity
            status = 'paid' if pay_direct else 'pending'
            cursor.execute('''INSERT INTO ticket_orders
                (order_no, user_id, ticket_id, quantity, unit_price, total_amount, visitor_name, visitor_phone, order_status, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (order_no, user['id'], ticket_id, quantity, unit_price, total_amount, visitor_name, visitor_phone, status, payload.get('remark') or ''))
            cursor.execute('UPDATE tickets SET stock = stock - %s WHERE id = %s', (quantity, ticket_id))
        db.commit()
        return Result(200, '支付成功' if pay_direct else '订单创建成功', {'order_no': order_no, 'order_status': status})
    except Exception as exc:
        db.rollback()
        return Result(500, f'订单创建失败：{exc}')


@router.get('/api/orders')
def list_my_orders(identity: dict = Depends(get_user_identity), db=Depends(get_db)):
    if identity.get('type') != 'user':
        return Result(401 if identity.get('type') != 'guest' else 403, '请登录后查看订单')
    with db.cursor() as cursor:
        cursor.execute('''SELECT o.*, t.name AS ticket_name, t.ticket_type
                         FROM ticket_orders o JOIN users u ON u.id = o.user_id
                         JOIN tickets t ON t.id = o.ticket_id
                         WHERE u.phone = %s ORDER BY o.created_at DESC''', (identity.get('id'),))
        items = [order_payload(row) for row in cursor.fetchall()]
    return Result(200, 'success', {'orders': items})


@router.get('/api/orders/{order_no}')
def get_my_order(order_no: str, identity: dict = Depends(get_user_identity), db=Depends(get_db)):
    if identity.get('type') != 'user':
        return Result(401, '请登录后查看订单')
    with db.cursor() as cursor:
        cursor.execute('''SELECT o.*, t.name AS ticket_name, t.ticket_type
                         FROM ticket_orders o JOIN users u ON u.id = o.user_id
                         JOIN tickets t ON t.id = o.ticket_id
                         WHERE o.order_no = %s AND u.phone = %s''', (order_no, identity.get('id')))
        row = cursor.fetchone()
    if not row:
        return Result(404, '订单不存在')
    return Result(200, 'success', {'order': order_payload(row)})


@router.post('/api/orders/{order_no}/refund')
def refund_order(order_no: str, identity: dict = Depends(get_user_identity), db=Depends(get_db)):
    """用户申请退票：已支付 → 已退款，恢复库存"""
    if identity.get('type') != 'user':
        return Result(401, '请登录后操作')
    try:
        with db.cursor() as cursor:
            cursor.execute('''SELECT o.*, u.phone FROM ticket_orders o
                             JOIN users u ON u.id = o.user_id
                             WHERE o.order_no = %s AND u.phone = %s FOR UPDATE''',
                           (order_no, identity.get('id')))
            row = cursor.fetchone()
            if not row:
                return Result(404, '订单不存在')
            if row['order_status'] != 'paid':
                return Result(400, f'当前状态"{row["order_status"]}"不支持退票')
            cursor.execute('UPDATE ticket_orders SET order_status = %s WHERE order_no = %s',
                           ('refunded', order_no))
            cursor.execute('UPDATE tickets SET stock = stock + %s WHERE id = %s',
                           (int(row['quantity']), int(row['ticket_id'])))
        db.commit()
        return Result(200, '退票成功', {'order_no': order_no, 'order_status': 'refunded'})
    except Exception as exc:
        db.rollback()
        return Result(500, f'退票失败：{exc}')