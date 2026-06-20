# ==================== 路线模块 ====================
# 接口09-10：路线列表 / 路线推荐
from fastapi import APIRouter, Depends, Query
from typing import Optional
from dependencies import get_db
from utils.response import Result

router = APIRouter()

def _assemble_route(cursor, row):
    route = {
        "id": row["id"], "name": row["name"], "duration": row["duration"],
        "difficulty": row["difficulty"], "description": row["description"],
        "hours_min": row["hours_min"], "hours_max": row["hours_max"],
    }
    if row["spot_ids"]:
        ids = [int(i) for i in row["spot_ids"].split(",") if i.strip().isdigit()]
        if ids:
            fmt = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"SELECT id, name, duration, tips FROM spots WHERE id IN ({fmt}) ORDER BY FIELD(id, {fmt})",
                ids + ids
            )
            route["spots"] = [
                {"id": s["id"], "name": s["name"], "duration": s["duration"], "tips": s["tips"]}
                for s in cursor.fetchall()
            ]
        else:
            route["spots"] = []
    else:
        route["spots"] = []
    return route

# ===== 接口09：路线列表 =====
# 前端：GET /api/routes
# 返回：{code, msg, data: {routes: [{id, name, duration, difficulty, description, hours_min, hours_max, spots: [...]}]}}
@router.get("/api/routes")
def get_routes(db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max "
                "FROM routes WHERE is_active = TRUE ORDER BY hours_min ASC"
            )
            rows = cursor.fetchall()
            routes = [_assemble_route(cursor, r) for r in rows]
        return Result(200, "success", {"routes": routes})
    except Exception as e:
        print(f"[routes 错误] {e}")
        return Result(50001, "获取路线失败")

# ===== 接口10：路线推荐 =====
# 前端：GET /api/routes/recommend?hours=4                     → 按时长推荐
# 前端：GET /api/routes/recommend?difficulty=轻松              → 按难度推荐
# 前端：GET /api/routes/recommend?interest=亲子                → 按兴趣推荐（自动转难度）
# 前端：GET /api/routes/recommend                              → 不传参数返回全部路线
# 三个参数可选，优先级：difficulty > hours > interest
# 支持的兴趣词：历史/文化/佛教/艺术/自然/风光/摄影/亲子/家庭/儿童/老人/入门/休闲
@router.get("/api/routes/recommend")
def recommend_route(
    hours: Optional[int] = Query(None, ge=1, le=24),
    difficulty: Optional[str] = Query(None, max_length=20),
    interest: Optional[str] = Query(None, max_length=30),
    db=Depends(get_db),
):
    interest_map = {
        "历史": "深度", "文化": "深度", "佛教": "深度", "艺术": "深度",
        "自然": "普通", "风光": "普通", "摄影": "普通", "太湖": "普通",
        "亲子": "轻松", "家庭": "轻松", "儿童": "轻松", "老人": "轻松",
        "入门": "入门", "休闲": "入门", "时间少": "入门",
    }
    if interest and not difficulty:
        for keyword, mapped_difficulty in interest_map.items():
            if keyword in interest:
                difficulty = mapped_difficulty
                break

    try:
        with db.cursor() as cursor:
            if difficulty:
                cursor.execute(
                    "SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max "
                    "FROM routes WHERE difficulty = %s AND is_active = TRUE LIMIT 1", (difficulty,)
                )
                r = cursor.fetchone()
                if not r:
                    return Result(40400, f"未找到[{difficulty}]难度的路线")
                return Result(200, "success", {"route": _assemble_route(cursor, r)})

            if hours is not None:
                cursor.execute(
                    "SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max, "
                    "ABS((hours_min + hours_max) / 2 - %s) AS gap "
                    "FROM routes WHERE is_active = TRUE ORDER BY gap ASC LIMIT 1", (hours,)
                )
                r = cursor.fetchone()
                if not r:
                    return Result(40400, "暂无合适路线")
                route = _assemble_route(cursor, r)
                hint = f"为您推荐【{route['name']}】(适合 {r['hours_min']}-{r['hours_max']} 小时)。"
                if hours < r["hours_min"]:
                    hint += " 提示：时间略紧，建议精简部分景点。"
                elif hours > r["hours_max"]:
                    hint += " 提示：时间充裕，可在各景点慢慢欣赏。"
                return Result(200, "success", {"route": route, "hint": hint})

            # 无参数：返回全部
            cursor.execute(
                "SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max "
                "FROM routes WHERE is_active = TRUE ORDER BY hours_min ASC"
            )
            rows = cursor.fetchall()
            return Result(200, "success", {"routes": [_assemble_route(cursor, r) for r in rows]})
    except Exception as e:
        print(f"[recommend 错误] {e}")
        return Result(50001, "推荐路线失败")
