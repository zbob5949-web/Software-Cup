from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from app.database import get_db_connection
from app.dependencies import get_current_user
from fastapi import Depends
import pymysql

router = APIRouter()

def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}

def require_login(phone: Optional[str] = Depends(get_current_user)) -> str:
    return phone

# 接口12：添加收藏
@router.post("/api/favorites/{spot_id}")
def add_favorite(spot_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM spots WHERE id = %s AND is_active = TRUE", (spot_id,))
            if not cursor.fetchone(): return Result(40400, "景点不存在")
            try:
                cursor.execute("INSERT INTO favorites (phone, spot_id) VALUES (%s, %s)", (phone, spot_id))
                conn.commit()
                return Result(200, "收藏成功")
            except pymysql.err.IntegrityError:
                return Result(40900, "已收藏过该景点")
    except Exception as e:
        conn.rollback()
        return Result(50001, "收藏失败")
    finally:
        conn.close()

# 接口13取消收藏
@router.delete("/api/favorites/{spot_id}")
def remove_favorite(spot_id: int, phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
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

# 接口14：我的收藏列表
@router.get("/api/favorites")
def get_favorites(phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
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
                {"id": r[0], "name": r[1], "category": r[2],
                 "description": r[3], "image_url": r[4], "favorited_at": str(r[5])}
                for r in rows
            ]
        return Result(200, "success", {"favorites": favorites})
    except Exception as e:
        return Result(50001, "获取收藏列表失败")
    finally:
        conn.close()