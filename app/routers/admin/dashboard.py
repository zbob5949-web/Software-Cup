from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import date_to_str, extract_hot_keywords, ok, semantic_cluster_questions

router = APIRouter()


@router.get("/api/admin/dashboard/overview")
@router.get("/admin/dashboard/overview")
def dashboard_overview(
    days: int = Query(7, ge=1, le=90),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT
              COUNT(DISTINCT CASE WHEN DATE(created_at)=CURDATE() THEN session_id END) AS today_sessions,
              COUNT(DISTINCT CASE WHEN YEARWEEK(created_at, 1)=YEARWEEK(CURDATE(), 1) THEN session_id END) AS week_sessions,
              COUNT(DISTINCT CASE WHEN DATE(created_at)=CURDATE() THEN COALESCE(phone, session_id) END) AS today_people,
              COUNT(DISTINCT CASE WHEN YEARWEEK(created_at, 1)=YEARWEEK(CURDATE(), 1) THEN COALESCE(phone, session_id) END) AS week_people
            FROM chat_records
            WHERE role = 'user'
            """
        )
        people = cursor.fetchone()

        cursor.execute(
            """
            SELECT content
            FROM chat_records
            WHERE role = 'user' AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY created_at DESC
            LIMIT 1000
            """,
            (days,),
        )
        recent_questions = [r["content"] for r in cursor.fetchall()]
        top_questions = semantic_cluster_questions(recent_questions, 10)
        hot_keywords = extract_hot_keywords(recent_questions[:500])

        cursor.execute(
            """
            SELECT DATE(created_at) AS day, COUNT(*) AS total, AVG(rating) AS avg_rating
            FROM feedbacks
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            """,
            (days,),
        )
        satisfaction_trend = [
            {"date": date_to_str(r["day"]), "total": r["total"], "avg_rating": round(float(r["avg_rating"] or 0), 2)}
            for r in cursor.fetchall()
        ]

        cursor.execute(
            """
            SELECT COALESCE(source, 'unknown') AS source, COUNT(*) AS cnt
            FROM chat_records
            WHERE role = 'assistant' AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY COALESCE(source, 'unknown')
            """,
            (days,),
        )
        source_counts = {r["source"]: r["cnt"] for r in cursor.fetchall()}
        answered = sum(source_counts.values()) or 1
        faq_count = source_counts.get("faq", 0)
        ai_count = (
            source_counts.get("ai", 0)
            + source_counts.get("dify", 0)
            + source_counts.get("local", 0)
            + source_counts.get("spot", 0)
            + source_counts.get("route", 0)
            + source_counts.get("service", 0)
        )
        source_ratio = {
            "counts": source_counts,
            "faq_hit_rate": round(faq_count / answered, 4),
            "ai_answer_rate": round(ai_count / answered, 4),
            "rag_answer_rate": round(source_counts.get("dify", 0) / answered, 4),
        }
    return ok({
        "conversation_people": people,
        "top_questions": top_questions,
        "hot_keywords": hot_keywords,
        "satisfaction_trend": satisfaction_trend,
        "source_ratio": source_ratio,
    })
