"""
反馈路由：提交反馈、查看我的反馈、反馈统计
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from app.database import get_db_connection
from app.dependencies import get_current_user, get_current_user_optional, get_user_identity

router = APIRouter()


def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}


def require_login(identity: dict = Depends(get_user_identity)) -> str:
    """要求正式用户登录，游客返回 403"""
    if identity["type"] == "guest":
        raise HTTPException(status_code=403, detail="游客模式下无法查看反馈历史，请注册登录")
    if identity["type"] == "anonymous":
        raise HTTPException(status_code=401, detail="请先登录")
    return identity["id"]


class FeedbackForm(BaseModel):
    type: str = ""
    rating: int = 5
    content: str = ""


# 接口9：提交反馈（允许游客和未登录用户提交）
@router.post("/api/feedback")
def submit_feedback(
    form: FeedbackForm,
    phone: Optional[str] = Depends(get_current_user_optional),
    identity: dict = Depends(get_user_identity),
):
    if not form.type:
        return Result(40001, "请选择反馈类型")
    if not (1 <= form.rating <= 5):
        return Result(40002, "评分需在1-5之间")
    if not form.content or not form.content.strip():
        return Result(40003, "请填写反馈内容")

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")

    # 确定提交者标识
    if identity["type"] == "user":
        submitter = phone  # 手机号
    elif identity["type"] == "guest":
        submitter = identity["id"]  # guest_xxx
    else:
        submitter = None  # 匿名

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """INSERT INTO feedbacks (phone, type, rating, content)
                   VALUES (%s, %s, %s, %s)""",
                (submitter, form.type, form.rating, form.content.strip())
            )
            conn.commit()
        return Result(200, "感谢您的反馈！")
    except Exception as e:
        conn.rollback()
        return Result(50001, "提交失败，请稍后重试")
    finally:
        conn.close()


# 接口10：我的反馈列表（必须正式用户登录）
@router.get("/api/feedback/mine")
def get_my_feedbacks(phone: str = Depends(require_login)):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """SELECT id, type, rating, content, status, created_at
                   FROM feedbacks WHERE phone = %s ORDER BY created_at DESC""",
                (phone,)
            )
            rows = cursor.fetchall()
            feedbacks = [
                {
                    "id": r["id"], "type": r["type"], "rating": r["rating"],
                    "content": r["content"], "status": r["status"],
                    "created_at": str(r["created_at"])
                }
                for r in rows
            ]
        return Result(200, "success", {"feedbacks": feedbacks})
    except Exception as e:
        return Result(50001, "获取反馈记录失败")
    finally:
        conn.close()


# 接口11：反馈统计分析（无需登录，保持不变）
@router.get("/api/feedback/stats")
def feedback_stats():
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), AVG(rating) FROM feedbacks")
            row = cursor.fetchone()
            total = row["COUNT(*)"] or 0
            avg_rating = round(float(row["AVG(rating)"]), 2) if row["AVG(rating)"] else 0

            cursor.execute(
                """SELECT type, COUNT(*) as cnt, AVG(rating) as avg_r
                   FROM feedbacks GROUP BY type ORDER BY cnt DESC"""
            )
            by_type = [
                {
                    "type": r["type"], "count": r["cnt"],
                    "avg_rating": round(float(r["avg_r"]), 2)
                }
                for r in cursor.fetchall()
            ]

            cursor.execute(
                "SELECT rating, COUNT(*) FROM feedbacks GROUP BY rating ORDER BY rating DESC"
            )
            distribution = [
                {"rating": r["rating"], "count": r["COUNT(*)"]}
                for r in cursor.fetchall()
            ]

            conclusions = []
            if avg_rating:
                if avg_rating >= 4.5:
                    conclusions.append("整体满意度优秀，游客体验良好。")
                elif avg_rating >= 3.5:
                    conclusions.append("整体满意度良好，仍有提升空间。")
                else:
                    conclusions.append("整体满意度偏低，需重点关注服务质量。")
                for t in by_type:
                    if t["avg_rating"] < 3.0:
                        conclusions.append(
                            f"「{t['type']}」类反馈评分较低（{t['avg_rating']}分），建议重点改善。"
                        )
                    elif t["avg_rating"] >= 4.5:
                        conclusions.append(
                            f"「{t['type']}」类反馈评分优秀（{t['avg_rating']}分），值得保持。"
                        )

        return Result(200, "success", {
            "total": total,
            "avg_rating": avg_rating,
            "by_type": by_type,
            "distribution": distribution,
            "conclusions": conclusions
        })
    except Exception as e:
        return Result(50001, "获取统计数据失败")
    finally:
        conn.close()
