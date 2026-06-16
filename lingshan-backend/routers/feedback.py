# ==================== 反馈模块 ====================
# 接口21-23：提交反馈 / 我的反馈 / 反馈统计
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from dependencies import get_current_user, get_current_user_optional, get_db
from utils.response import Result
from core.config import MAX_FEEDBACK_CONTENT_LENGTH

router = APIRouter()

def require_login(phone: str = Depends(get_current_user)) -> str:
    return phone

class FeedbackForm(BaseModel):
    type: str = Field("", max_length=20)       # 反馈类型（如"建议"、"投诉"、"表扬"）
    rating: int = 5      # 评分 1-5
    content: str = Field("", max_length=MAX_FEEDBACK_CONTENT_LENGTH)    # 反馈内容

# ===== 接口21：提交反馈（允许未登录） =====
# 前端：POST /api/feedback  body: {type: "建议", rating: 5, content: "景区很棒！"}
# 登录后提交会自动关联手机号，未登录也可提交
@router.post("/api/feedback")
def submit_feedback(
    form: FeedbackForm,
    phone: Optional[str] = Depends(get_current_user_optional),
    db=Depends(get_db),
):
    if not form.type:
        return Result(40001, "请选择反馈类型")
    if form.type not in {"建议", "投诉", "表扬", "其他"}:
        return Result(40004, "反馈类型不支持")
    if not (1 <= form.rating <= 5):
        return Result(40002, "评分需在1-5之间")
    if not form.content or not form.content.strip():
        return Result(40003, "请填写反馈内容")
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO feedbacks (phone, type, rating, content) VALUES (%s, %s, %s, %s)",
                (phone, form.type, form.rating, form.content.strip())
            )
            db.commit()
        return Result(200, "感谢您的反馈！")
    except Exception as e:
        db.rollback()
        return Result(50001, "提交失败，请稍后重试")

# ===== 接口22：我的反馈列表（需登录） =====
# 前端：GET /api/feedback/mine  (Header: Authorization: Bearer <token>)
# 返回：{code, msg, data: {feedbacks: [{id, type, rating, content, status, created_at}]}}
@router.get("/api/feedback/mine")
def get_my_feedbacks(phone: str = Depends(require_login), db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT id, type, rating, content, status, created_at "
                "FROM feedbacks WHERE phone = %s ORDER BY created_at DESC", (phone,)
            )
            rows = cursor.fetchall()
            feedbacks = [
                {"id": r["id"], "type": r["type"], "rating": r["rating"],
                 "content": r["content"], "status": r["status"], "created_at": str(r["created_at"])}
                for r in rows
            ]
        return Result(200, "success", {"feedbacks": feedbacks})
    except Exception as e:
        return Result(50001, "获取反馈记录失败")

# ===== 接口23：反馈统计分析（无需登录） =====
# 前端：GET /api/feedback/stats
# 返回：{total, avg_rating, by_type, distribution, conclusions}
# 说明：用于管理后台数据看板，展示整体满意度、分类统计、评分分布、自动结论
@router.get("/api/feedback/stats")
def feedback_stats(db=Depends(get_db)):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), AVG(rating) FROM feedbacks")
            row = cursor.fetchone()
            total, avg_rating = row["COUNT(*)"], row["AVG(rating)"]
            avg_rating = round(float(avg_rating), 2) if avg_rating else 0
            total = total or 0
            cursor.execute(
                "SELECT type, COUNT(*) as cnt, AVG(rating) as avg_r "
                "FROM feedbacks GROUP BY type ORDER BY cnt DESC"
            )
            by_type = [
                {"type": r["type"], "count": r["cnt"], "avg_rating": round(float(r["avg_r"]), 2)}
                for r in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT rating, COUNT(*) FROM feedbacks GROUP BY rating ORDER BY rating DESC"
            )
            distribution = [{"rating": r["rating"], "count": r["COUNT(*)"]} for r in cursor.fetchall()]
            conclusions = []
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
            "total": total, "avg_rating": avg_rating,
            "by_type": by_type, "distribution": distribution,
            "conclusions": conclusions
        })
    except Exception as e:
        return Result(50001, "获取统计数据失败")
