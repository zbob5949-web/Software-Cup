from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import date_to_str, ok
from app.utils.response import Result

router = APIRouter()


def value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def spot_row(row):
    return {key: value(row.get(key)) for key in ('id', 'name', 'category', 'description', 'open_time', 'duration', 'tips', 'sort_order', 'image_url', 'is_active', 'created_at')}


def ticket_row(row):
    status = row.get('status') or 'off_sale'
    return {
        'id': row.get('id'),
        'code': str(row.get('id')),
        'name': row.get('name') or '',
        'price': value(row.get('price')),
        'note': row.get('description') or '',
        'ticket_type': row.get('ticket_type') or '',
        'stock': row.get('stock') or 0,
        'status': status,
        'sort_order': row.get('id') or 0,
        'is_active': status == 'on_sale',
        'created_at': value(row.get('created_at')),
        'updated_at': value(row.get('updated_at')),
    }


@router.get('/api/tickets')
def public_tickets(db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute("SELECT id, name, ticket_type, price, stock, status, description, created_at, updated_at FROM tickets WHERE status = 'on_sale' ORDER BY id ASC")
        items = [ticket_row(row) for row in cursor.fetchall()]
    return ok({'tickets': items})


@router.get('/api/admin/spots')
def list_admin_spots(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url, is_active, created_at FROM spots ORDER BY sort_order ASC, id ASC')
        items = [spot_row(row) for row in cursor.fetchall()]
    return ok({'spots': items})


@router.post('/api/admin/spots')
def create_admin_spot(payload: dict, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    name = str(payload.get('name') or '').strip()
    if not name:
        return Result(400, '景点名称不能为空')
    try:
        with db.cursor() as cursor:
            cursor.execute('''INSERT INTO spots (name, category, description, open_time, duration, tips, sort_order, image_url, is_active)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''', (
                name, payload.get('category') or '景点', payload.get('description') or '',
                payload.get('open_time') or '', payload.get('duration') or '', payload.get('tips') or '',
                int(payload.get('sort_order') or 0), payload.get('image_url'), bool(payload.get('is_active', True)),
            ))
            item_id = cursor.lastrowid
        db.commit()
        return ok({'id': item_id}, '景点创建成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'景点创建失败：{exc}')


@router.put('/api/admin/spots/{spot_id}')
def update_admin_spot(spot_id: int, payload: dict, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    fields, params = [], []
    for field in ('name', 'category', 'description', 'open_time', 'duration', 'tips', 'sort_order', 'image_url', 'is_active'):
        if field in payload:
            fields.append(f'{field} = %s')
            params.append(bool(payload[field]) if field == 'is_active' else payload[field])
    if not fields:
        return Result(400, '没有需要更新的字段')
    try:
        with db.cursor() as cursor:
            cursor.execute(f'UPDATE spots SET {", ".join(fields)} WHERE id = %s', params + [spot_id])
            if cursor.rowcount == 0:
                return Result(404, '景点不存在')
        db.commit()
        return ok({'id': spot_id}, '景点更新成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'景点更新失败：{exc}')


@router.get('/api/admin/tickets')
def list_admin_tickets(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('SELECT id, name, ticket_type, price, stock, status, description, created_at, updated_at FROM tickets ORDER BY id ASC')
        items = [ticket_row(row) for row in cursor.fetchall()]
    return ok({'tickets': items})


@router.post('/api/admin/tickets')
def create_admin_ticket(payload: dict, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    name = str(payload.get('name') or '').strip()
    if not name:
        return Result(400, '票种名称不能为空')
    try:
        with db.cursor() as cursor:
            cursor.execute('''INSERT INTO tickets (name, ticket_type, price, stock, status, description)
                              VALUES (%s, %s, %s, %s, %s, %s)''', (
                name, payload.get('ticket_type') or '门票', float(payload.get('price') or 0),
                int(payload.get('stock') or 0), 'on_sale' if bool(payload.get('is_active', True)) else 'off_sale',
                payload.get('note') or '',
            ))
            item_id = cursor.lastrowid
        db.commit()
        return ok({'id': item_id}, '票种创建成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'票种创建失败：{exc}')


@router.put('/api/admin/tickets/{ticket_id}')
def update_admin_ticket(ticket_id: int, payload: dict, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    fields, params = [], []
    mapping = {'name': 'name', 'ticket_type': 'ticket_type', 'price': 'price', 'stock': 'stock', 'note': 'description'}
    for source, column in mapping.items():
        if source in payload:
            fields.append(f'{column} = %s')
            params.append(float(payload[source]) if source == 'price' else payload[source])
    if 'is_active' in payload:
        fields.append('status = %s')
        params.append('on_sale' if payload['is_active'] else 'off_sale')
    if not fields:
        return Result(400, '没有需要更新的字段')
    try:
        with db.cursor() as cursor:
            cursor.execute(f'UPDATE tickets SET {", ".join(fields)} WHERE id = %s', params + [ticket_id])
            if cursor.rowcount == 0:
                return Result(404, '票种不存在')
        db.commit()
        return ok({'id': ticket_id}, '票种更新成功')
    except Exception as exc:
        db.rollback()
        return Result(500, f'票种更新失败：{exc}')


@router.get('/api/admin/favorites')
def list_admin_favorites(_: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        cursor.execute('''SELECT f.id, f.phone, f.spot_id, s.name AS spot_name, s.category, f.created_at
                         FROM favorites f LEFT JOIN spots s ON s.id = f.spot_id
                         ORDER BY f.created_at DESC''')
        items = [{
            'id': row.get('id'), 'phone': row.get('phone'), 'spot_id': row.get('spot_id'),
            'spot_name': row.get('spot_name') or '已删除景点', 'category': row.get('category') or '',
            'created_at': date_to_str(row.get('created_at')),
        } for row in cursor.fetchall()]
    return ok({'favorites': items, 'total': len(items)})


@router.delete('/api/admin/favorites/{favorite_id}')
def delete_admin_favorite(favorite_id: int, _: dict = Depends(get_current_admin_user), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute('DELETE FROM favorites WHERE id = %s', (favorite_id,))
            if cursor.rowcount == 0:
                return Result(404, '收藏记录不存在')
        db.commit()
        return ok({'id': favorite_id}, '收藏记录已删除')
    except Exception as exc:
        db.rollback()
        return Result(500, f'收藏记录删除失败：{exc}')