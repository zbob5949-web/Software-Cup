# ==================== 景点模块 ====================
# 接口05-08：景点列表/详情/搜索/兴趣推荐
from fastapi import APIRouter, Depends, Query
from dependencies import get_db
from utils.response import Result

router = APIRouter()

def _spot_row(row: dict, brief: bool = False):
    data = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "duration": row["duration"],
        "sort_order": row["sort_order"],
        "image_url": row["image_url"],
    }
    if not brief:
        data.update({
            "description": row["description"],
            "open_time": row["open_time"],
            "tips": row["tips"],
        })
    return data

# ===== 接口05：景点列表 =====
# 前端：GET /api/spots                     → 完整信息（含描述）
# 前端：GET /api/spots?brief=true          → 摘要信息（推荐列表页使用，省流量）
@router.get("/api/spots")
def get_spots(brief: bool = Query(False), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            if brief:
                # 列表页：只返回展示必需字段
                cursor.execute(
                    "SELECT id, name, category, duration, sort_order, image_url "
                    "FROM spots WHERE is_active = TRUE ORDER BY sort_order ASC"
                )
                rows = cursor.fetchall()
                spots = [_spot_row(r, brief=True) for r in rows]
            else:
                cursor.execute(
                    "SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url "
                    "FROM spots WHERE is_active = TRUE ORDER BY sort_order ASC"
                )
                rows = cursor.fetchall()
                spots = [_spot_row(r) for r in rows]
        return Result(200, "success", {"spots": spots, "total": len(spots)})
    except Exception as e:
        print(f"[spots 错误] {e}")
        return Result(50001, "获取景点失败")

# ===== 接口07：景点搜索 =====
# 前端：GET /api/spots/search?q=大佛  →  搜索名称/描述/类别匹配的景点
@router.get("/api/spots/search")
def search_spots(q: str = Query(..., min_length=1, max_length=50), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url "
                "FROM spots WHERE is_active = TRUE "
                "AND (name LIKE %s OR description LIKE %s OR category LIKE %s) "
                "ORDER BY sort_order ASC LIMIT 10",
                (f"%{q}%", f"%{q}%", f"%{q}%")
            )
            rows = cursor.fetchall()
            spots = [_spot_row(r) for r in rows]
        return Result(200, "success", {"spots": spots, "total": len(spots)})
    except Exception as e:
        print(f"[spots search 错误] {e}")
        return Result(50001, "搜索景点失败")

# ===== 接口08：按兴趣推荐景点 =====
# 前端：GET /api/spots/recommend?interest=佛教  →  推荐佛教相关景点
# 前端：GET /api/spots/recommend?interest=亲子  →  推荐亲子类景点
# 支持的兴趣：佛教/历史/文化/建筑/自然/风光/摄影/亲子/演出/祈福/禅意/艺术
@router.get("/api/spots/recommend")
def recommend_spots(
    interest: str = Query(..., min_length=1, max_length=30),
    db=Depends(get_db),
):
    category_map = {
        "佛教": ["佛像", "建筑"], "历史": ["建筑"], "文化": ["建筑", "体验"],
        "建筑": ["建筑"], "自然": ["自然"], "风光": ["自然"], "摄影": ["自然"],
        "亲子": ["体验", "演出"], "演出": ["演出"], "祈福": ["体验", "佛像"],
        "禅意": ["建筑", "体验"], "艺术": ["建筑"],
    }
    categories = category_map.get(interest, [interest])
    try:
        with db.cursor() as cursor:
            ph = ",".join(["%s"] * len(categories))
            cursor.execute(
                "SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url "
                f"FROM spots WHERE is_active = TRUE AND category IN ({ph}) "
                "ORDER BY sort_order ASC LIMIT 8", categories
            )
            rows = cursor.fetchall()
            spots = [_spot_row(r) for r in rows]
        return Result(200, "success", {"spots": spots, "interest": interest})
    except Exception as e:
        print(f"[spots recommend 错误] {e}")
        return Result(50001, "推荐景点失败")

# ===== 接口06：景点详情 =====
# 前端：GET /api/spots/11  →  获取灵山大佛完整信息
@router.get("/api/spots/{spot_id}")
def get_spot_detail(spot_id: int, db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url "
                "FROM spots WHERE id = %s AND is_active = TRUE", (spot_id,)
            )
            row = cursor.fetchone()
            if not row:
                return Result(40400, "景点不存在")
            spot = _spot_row(row)
        return Result(200, "success", {"spot": spot})
    except Exception as e:
        print(f"[spot_detail 错误] {e}")
        return Result(50001, "获取景点详情失败")
