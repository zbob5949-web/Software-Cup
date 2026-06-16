"""管理后台 - 数据大屏接口。

接口编号：ADMIN-DASH-01
用途：聚合聊天、反馈和回答来源数据，供运营数据大屏展示。
"""
from fastapi import APIRouter, Depends, Query

from dependencies import get_current_admin_user, get_db
from routers.admin.common import date_to_str, extract_hot_keywords, ok, semantic_cluster_questions

router = APIRouter()


# ADMIN-DASH-01：数据大屏总览接口，返回服务人次、热门问题、满意度和命中率。
@router.get("/api/admin/dashboard/overview")
@router.get("/admin/dashboard/overview")
def dashboard_overview(
    days: int = Query(7, ge=1, le=90),#days - 统计天数（1-90天，默认7天）
    _: dict = Depends(get_current_admin_user),#权限: 需要管理员登录（get_current_admin_user）
    db=Depends(get_db),
):
    """按最近 days 天聚合管理后台大屏所需的核心运营指标。"""
    with db.cursor() as cursor:
        # 会话人数统计 (conversation_people)
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

        # 热门问题 TOP10：改为本地语义聚类，而不是只按完全相同文本 GROUP BY。
        # 例如“门票多少钱 / 票价多少 / 怎么买票”会归为“门票/票价/购票”一类。
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

       # 热门关键词 (hot_keywords)，从最近对话中提取的高频词汇，使用公共工具函数 extract_hot_keywords 处理，最多返回10个关键词及其出现次数
        hot_keywords = extract_hot_keywords(recent_questions[:500])

        #满意度趋势 (satisfaction_trend)，每日反馈数量和平均评分趋势，评分已四舍五入保留2位小数
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

        #回答来源占比 (source_ratio)
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
        faq_count = source_counts.get("faq", 0)#FAQ: 标准问答库匹配
        ai_count = (#AI类: ai + dify + local + spot + route + service
            source_counts.get("ai", 0)
            + source_counts.get("dify", 0)
            + source_counts.get("local", 0)
            + source_counts.get("spot", 0)
            + source_counts.get("route", 0)
            + source_counts.get("service", 0)
        )
        source_ratio = {#RAG: 特指dify来源的检索增强生成
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
