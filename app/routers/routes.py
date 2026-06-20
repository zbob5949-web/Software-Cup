from fastapi import APIRouter, Query


from typing import Optional
from app.database import get_db_connection

router = APIRouter()

def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}

def _assemble_route(cursor, row):
    route = {
        "id": row["id"], "name": row["name"], "duration": row["duration"],
        "difficulty": row["difficulty"], "description": row["description"],
        "hours_min": row["hours_min"], "hours_max": row["hours_max"],
    }
    if row["spot_ids"]:
        # spot_ids 存的是 sort_order 值，需要映射到实际数据库 id
        sort_orders = [int(i) for i in row["spot_ids"].split(",") if i.strip().isdigit()]
        if sort_orders:
            fmt = ",".join(["%s"] * len(sort_orders))
            cursor.execute(
                f"SELECT id, name, duration, tips FROM spots WHERE sort_order IN ({fmt}) ORDER BY FIELD(sort_order, {fmt})",
                sort_orders + sort_orders
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

# 接口7：路线列表
@router.get("/api/routes")
def get_routes():
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max
                FROM routes WHERE is_active = TRUE ORDER BY hours_min ASC
            """)
            rows = cursor.fetchall()
            routes = [_assemble_route(cursor, r) for r in rows]
        return Result(200, "success", {"routes": routes})
    except Exception as e:
        print(f"[routes 错误] {e}")
        return Result(50001, "获取路线失败")
    finally:
        conn.close()

# 接口8：路线推荐
@router.get("/api/routes/recommend")
def recommend_route(
    hours: Optional[int] = Query(None, ge=1, le=24),
    difficulty: Optional[str] = Query(None),
    interest: Optional[str] = Query(None),
):
    # 兴趣关键词映射到难度
    interest_map = {
        "历史": "深度", "文化": "深度", "佛教": "深度", "艺术": "深度",
        "自然": "普通", "风光": "普通", "摄影": "普通", "太湖": "普通",
        "亲子": "轻松", "家庭": "轻松", "儿童": "轻松", "老人": "轻松",
        "入门": "入门", "休闲": "入门", "时间少": "入门",
    }
    # interest 命中后转成 difficulty 走原有逻辑
    if interest and not difficulty:
        for keyword, mapped_difficulty in interest_map.items():
            if keyword in interest:
                difficulty = mapped_difficulty
                break

    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            # 模式1：按难度查
            if difficulty:
                cursor.execute("""
                    SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max
                    FROM routes WHERE difficulty = %s AND is_active = TRUE LIMIT 1
                """, (difficulty,))
                r = cursor.fetchone()
                if not r: return Result(40400, f"未找到[{difficulty}]难度的路线")
                return Result(200, "success", {"route": _assemble_route(cursor, r)})

            # 模式2：按时长匹配最近路线
            if hours is not None:
                cursor.execute("""
                    SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max,
                           ABS((hours_min + hours_max) / 2 - %s) AS gap
                    FROM routes WHERE is_active = TRUE ORDER BY gap ASC LIMIT 1
                """, (hours,))
                r = cursor.fetchone()
                if not r: return Result(40400, "暂无合适路线")
                route = _assemble_route(cursor, r)
                hint = f"为您推荐【{route['name']}】(适合 {r['hours_min']}-{r['hours_max']} 小时)。"
                if hours < r["hours_min"]: hint += " 提示：时间略紧，建议精简部分景点。"
                elif hours > r["hours_max"]: hint += " 提示：时间充裕，可在各景点慢慢欣赏。"
                return Result(200, "success", {"route": route, "hint": hint})

            # 模式3：什么都没传，返回全部路线
            cursor.execute("""
                SELECT id, name, duration, difficulty, description, spot_ids, hours_min, hours_max
                FROM routes WHERE is_active = TRUE ORDER BY hours_min ASC
            """)
            rows = cursor.fetchall()
            return Result(200, "success", {"routes": [_assemble_route(cursor, r) for r in rows]})
    except Exception as e:
        print(f"[recommend 错误] {e}")
        return Result(50001, "推荐路线失败")
    finally:
        conn.close()
