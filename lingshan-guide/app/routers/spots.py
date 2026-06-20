from fastapi import APIRouter
from app.database import get_db_connection

router = APIRouter()

def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}

# 接口5：景点列表
@router.get("/api/spots")
def get_spots():
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url
                FROM spots WHERE is_active = TRUE ORDER BY sort_order ASC
            """)
            rows = cursor.fetchall()
            spots = [
                {"id": r[0], "name": r[1], "category": r[2], "description": r[3],
                 "open_time": r[4], "duration": r[5], "tips": r[6],
                 "sort_order": r[7], "image_url": r[8]}
                for r in rows
            ]
        return Result(200, "success", {"spots": spots})
    except Exception as e:
        print(f"[spots 错误] {e}")
        return Result(50001, "获取景点失败")
    finally:
        conn.close()

# 接口6：景点详情
@router.get("/api/spots/{spot_id}")
def get_spot_detail(spot_id: int):
    conn = get_db_connection()
    if not conn: return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, category, description, open_time, duration, tips, sort_order, image_url
                FROM spots WHERE id = %s AND is_active = TRUE
            """, (spot_id,))
            r = cursor.fetchone()
            if not r: return Result(40400, "景点不存在")
            spot = {"id": r[0], "name": r[1], "category": r[2], "description": r[3],
                    "open_time": r[4], "duration": r[5], "tips": r[6],
                    "sort_order": r[7], "image_url": r[8]}
        return Result(200, "success", {"spot": spot})
    except Exception as e:
        print(f"[spot_detail 错误] {e}")
        return Result(50001, "获取景点详情失败")
    finally:
        conn.close()