"""
收藏路由：景点收藏、路线收藏、票种收藏
仅正式用户可用，游客不可使用
"""

from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db_connection
from app.dependencies import get_current_user, get_user_identity
from pymysql.err import IntegrityError

router = APIRouter()


def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}


def require_login(identity: dict = Depends(get_user_identity)) -> str:
    """要求正式用户登录，游客返回403"""
    if identity["type"] == "guest":
        raise HTTPException(status_code=403, detail="游客模式下无法使用收藏功能，请注册登录")
    if identity["type"] == "anonymous":
        raise HTTPException(status_code=401, detail="请先登录")
    return identity["id"]


# ==================== 景点收藏 ====================

@router.post("/api/favorites/{spot_id}")
def add_favorite(spot_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM spots WHERE id = %s AND is_active = TRUE", (spot_id,))
            if not cursor.fetchone():
                return Result(40400, "景点不存在")
            try:
                cursor.execute(
                    "INSERT INTO favorites (phone, spot_id) VALUES (%s, %s)",
                    (phone, spot_id)
                )
                conn.commit()
                return Result(200, "收藏成功")
            except IntegrityError:
                return Result(40900, "已收藏过该景点")
    except Exception as e:
        conn.rollback()
        return Result(50001, "收藏失败")
    finally:
        conn.close()


@router.delete("/api/favorites/{spot_id}")
def remove_favorite(spot_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM favorites WHERE phone = %s AND spot_id = %s",
                (phone, spot_id)
            )
            if cursor.rowcount == 0:
                return Result(40400, "该景点未收藏")
            conn.commit()
        return Result(200, "已取消收藏")
    except Exception as e:
        conn.rollback()
        return Result(50001, "取消收藏失败")
    finally:
        conn.close()


@router.get("/api/favorites")
def get_favorites(phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT s.id, s.name, s.category, s.description, s.image_url, f.created_at
                FROM favorites f JOIN spots s ON f.spot_id = s.id
                WHERE f.phone = %s AND s.is_active = TRUE
                ORDER BY f.created_at DESC
            """, (phone,))
            rows = cursor.fetchall()
            favorites = [
                {
                    "id": r["id"], "name": r["name"], "category": r["category"],
                    "description": r["description"], "image_url": r["image_url"],
                    "favorited_at": str(r["created_at"])
                }
                for r in rows
            ]
        return Result(200, "success", {"favorites": favorites})
    except Exception as e:
        return Result(50001, "获取收藏列表失败")
    finally:
        conn.close()


# ==================== 路线收藏 ====================

@router.post("/api/favorites/route/{route_id}")
def add_route_favorite(route_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM routes WHERE id = %s AND is_active = TRUE", (route_id,))
            if not cursor.fetchone():
                return Result(40400, "路线不存在")
            try:
                cursor.execute(
                    "INSERT INTO route_favorites (phone, route_id) VALUES (%s, %s)",
                    (phone, route_id)
                )
                conn.commit()
                return Result(200, "收藏成功")
            except IntegrityError:
                return Result(40900, "已收藏过该路线")
    except Exception as e:
        conn.rollback()
        return Result(50001, "收藏失败")
    finally:
        conn.close()


@router.delete("/api/favorites/route/{route_id}")
def remove_route_favorite(route_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM route_favorites WHERE phone = %s AND route_id = %s",
                (phone, route_id)
            )
            if cursor.rowcount == 0:
                return Result(40400, "该路线未收藏")
            conn.commit()
        return Result(200, "已取消收藏")
    except Exception as e:
        conn.rollback()
        return Result(50001, "取消收藏失败")
    finally:
        conn.close()


@router.get("/api/favorites/route")
def get_route_favorites(phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.id, r.name, r.duration, r.difficulty, r.description, f.created_at
                FROM route_favorites f JOIN routes r ON f.route_id = r.id
                WHERE f.phone = %s AND r.is_active = TRUE
                ORDER BY f.created_at DESC
            """, (phone,))
            rows = cursor.fetchall()
            favorites = [
                {
                    "id": r["id"], "name": r["name"], "duration": r["duration"],
                    "difficulty": r["difficulty"], "description": r["description"],
                    "favorited_at": str(r["created_at"])
                }
                for r in rows
            ]
        return Result(200, "success", {"favorites": favorites})
    except Exception as e:
        return Result(50001, "获取收藏列表失败")
    finally:
        conn.close()


# ==================== 票种收藏 ====================

@router.post("/api/favorites/ticket/{ticket_id}")
def add_ticket_favorite(ticket_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM tickets WHERE id = %s AND status = 'on_sale'", (ticket_id,))
            if not cursor.fetchone():
                return Result(40400, "票种不存在或已停售")
            try:
                cursor.execute(
                    "INSERT INTO ticket_favorites (phone, ticket_id) VALUES (%s, %s)",
                    (phone, ticket_id)
                )
                conn.commit()
                return Result(200, "收藏成功")
            except IntegrityError:
                return Result(40900, "已收藏过该票种")
    except Exception as e:
        conn.rollback()
        return Result(50001, "收藏失败")
    finally:
        conn.close()


@router.delete("/api/favorites/ticket/{ticket_id}")
def remove_ticket_favorite(ticket_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM ticket_favorites WHERE phone = %s AND ticket_id = %s",
                (phone, ticket_id)
            )
            if cursor.rowcount == 0:
                return Result(40400, "该票种未收藏")
            conn.commit()
        return Result(200, "已取消收藏")
    except Exception as e:
        conn.rollback()
        return Result(50001, "取消收藏失败")
    finally:
        conn.close()


@router.get("/api/favorites/ticket")
def get_ticket_favorites(phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT t.id, t.name, t.ticket_type, t.price, t.description, f.created_at
                FROM ticket_favorites f JOIN tickets t ON f.ticket_id = t.id
                WHERE f.phone = %s AND t.status = 'on_sale'
                ORDER BY f.created_at DESC
            """, (phone,))
            rows = cursor.fetchall()
            favorites = [
                {
                    "id": r["id"], "name": r["name"], "ticket_type": r["ticket_type"],
                    "price": float(r["price"]), "description": r["description"],
                    "favorited_at": str(r["created_at"])
                }
                for r in rows
            ]
        return Result(200, "success", {"favorites": favorites})
    except Exception as e:
        return Result(50001, "获取收藏列表失败")
    finally:
        conn.close()