# ==================== 收藏模块 ====================
# 接口18-20：我的收藏 / 添加收藏 / 取消收藏
from fastapi import APIRouter, Depends
from typing import Optional
from dependencies import get_current_user, get_db
from utils.response import Result
import pymysql

router = APIRouter()

def require_login(phone: Optional[str] = Depends(get_current_user)) -> str:
    return phone

# ===== 接口18：我的收藏列表（需登录） =====
# 前端：GET /api/favorites  (Header: Authorization: Bearer <token>)
# 返回：{code, msg, data: {favorites: [{id, name, category, description, image_url, favorited_at}]}}
@router.get("/api/favorites")
def get_favorites(phone: str = Depends(require_login), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT s.id, s.name, s.category, s.description, s.image_url, f.created_at "
                "FROM favorites f JOIN spots s ON f.spot_id = s.id "
                "WHERE f.phone = %s AND s.is_active = TRUE "
                "ORDER BY f.created_at DESC", (phone,)
            )
            rows = cursor.fetchall()
            favorites = [
                {"id": r["id"], "name": r["name"], "category": r["category"],
                 "description": r["description"], "image_url": r["image_url"],
                 "favorited_at": str(r["created_at"])}
                for r in rows
            ]
        return Result(200, "success", {"favorites": favorites})
    except Exception as e:
        return Result(50001, "获取收藏列表失败")

# ===== 接口19：添加收藏（需登录） =====
# 前端：POST /api/favorites/11  →  收藏id=11的景点（灵山大佛）
# 返回：{code, msg}  200=成功 / 40900=已收藏 / 40400=景点不存在
@router.post("/api/favorites/{spot_id}")
def add_favorite(spot_id: int, phone: str = Depends(require_login), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM spots WHERE id = %s AND is_active = TRUE", (spot_id,))
            if not cursor.fetchone():
                return Result(40400, "景点不存在")
            try:
                cursor.execute(
                    "INSERT INTO favorites (phone, spot_id) VALUES (%s, %s)", (phone, spot_id)
                )
                db.commit()
                return Result(200, "收藏成功")
            except pymysql.err.IntegrityError:
                db.rollback()
                return Result(40900, "已收藏过该景点")
    except Exception as e:
        db.rollback()
        return Result(50001, "收藏失败")

# ===== 接口20：取消收藏（需登录） =====
# 前端：DELETE /api/favorites/11  →  取消收藏id=11的景点
# 返回：{code, msg}  200=成功 / 40400=未收藏
@router.delete("/api/favorites/{spot_id}")
def remove_favorite(spot_id: int, phone: str = Depends(require_login), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM favorites WHERE phone = %s AND spot_id = %s", (phone, spot_id)
            )
            if cursor.rowcount == 0:
                return Result(40400, "该景点未收藏")
            db.commit()
        return Result(200, "已取消收藏")
    except Exception as e:
        db.rollback()
        return Result(50001, "取消收藏失败")
