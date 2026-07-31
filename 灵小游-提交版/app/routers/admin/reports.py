import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends

from app.core.config import DEEPSEEK_KEY
from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import extract_hot_keywords, ok
from app.services.chat_service import call_deepseek
from app.utils.response import Result

router = APIRouter()

POSITIVE_WORDS = {"喜欢", "满意", "不错", "很好", "好玩", "漂亮", "震撼", "方便", "推荐", "开心", "舒适", "赞"}
NEGATIVE_WORDS = {"差", "不满", "失望", "太贵", "排队", "拥挤", "找不到", "不好", "慢", "脏", "累", "投诉", "迷路"}


def local_sentiment(text: str) -> tuple[str, int]:
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos > neg:
        return "positive", pos - neg
    if neg > pos:
        return "negative", neg - pos
    return "neutral", 0


def ai_sentiment_summary(messages: list[str], counts: dict) -> dict | None:
    if not DEEPSEEK_KEY or not messages:
        return None
    sample = messages[:80]
    prompt = (
        "你是景区运营分析师。请基于游客问题样本生成JSON，字段：summary、focus_points、suggestions。"
        "不要输出Markdown。情绪计数为："
        f"{counts}。游客问题样本：{json.dumps(sample, ensure_ascii=False)}"
    )
    raw = call_deepseek([
        {"role": "system", "content": "只输出合法JSON。"},
        {"role": "user", "content": prompt},
    ])
    if any(flag in raw for flag in ["不可用", "未配置", "服务异常", "请稍后再试"]):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return {"summary": raw[:500], "focus_points": [], "suggestions": []}


@router.get("/api/admin/reports/sentiment")
@router.get("/admin/reports/sentiment")
def sentiment_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    use_ai: bool = False,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=6))
    if start_date > end_date:
        return Result(400, "start_date不能晚于end_date")

    with db.cursor() as cursor:
        cursor.execute(
            """
            SELECT content, created_at
            FROM chat_records
            WHERE role='user' AND DATE(created_at) BETWEEN %s AND %s
            ORDER BY created_at ASC
            """,
            (start_date, end_date),
        )
        rows = cursor.fetchall()

    counts = {"positive": 0, "neutral": 0, "negative": 0}
    trend = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0, "total": 0})
    examples = {"positive": [], "neutral": [], "negative": []}
    texts = []
    for row in rows:
        text = row["content"] or ""
        texts.append(text)
        label, score = local_sentiment(text)
        day = row["created_at"].date().isoformat() if isinstance(row["created_at"], datetime) else str(row["created_at"])[:10]
        counts[label] += 1
        trend[day][label] += 1
        trend[day]["total"] += 1
        if len(examples[label]) < 5:
            examples[label].append({"text": text, "score": score})

    total = sum(counts.values())
    local_summary = "游客整体情绪平稳。"
    if total:
        if counts["negative"] / total >= 0.3:
            local_summary = "负向情绪占比较高，建议重点关注拥挤、排队、价格、路线指引等问题。"
        elif counts["positive"] / total >= 0.5:
            local_summary = "正向情绪占比较高，游客对景区体验整体认可。"

    ai_summary = ai_sentiment_summary(texts, counts) if use_ai else None
    suggestions = [
        "将热门问题补充进FAQ与Dify知识库，提升FAQ命中率。",
        "对负向高频词（如排队、迷路、太贵）建立专项运营改进项。",
        "在数字人回答中增加厕所、餐饮、观光车等即时服务指引。",
    ]
    response_data = {
        "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        "total_messages": total,
        "counts": counts,
        "trend": [{"date": k, **v} for k, v in sorted(trend.items())],
        "examples": examples,
        "summary": ai_summary.get("summary") if ai_summary else local_summary,
        "focus_points": ai_summary.get("focus_points") if ai_summary else extract_hot_keywords(texts, 8),
        "suggestions": ai_summary.get("suggestions") if ai_summary else suggestions,
        "analyzer": "deepseek" if ai_summary else "local_lexicon",
    }

    try:
        with db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sentiment_reports
                (period_start, period_end, source, summary, positive_count, neutral_count, negative_count, suggestions)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    start_date,
                    end_date,
                    response_data["analyzer"],
                    response_data["summary"],
                    counts["positive"],
                    counts["neutral"],
                    counts["negative"],
                    json.dumps(response_data["suggestions"], ensure_ascii=False),
                ),
            )
            response_data["report_id"] = cursor.lastrowid
        db.commit()
    except Exception as exc:
        db.rollback()
        response_data["persist_warning"] = f"报告生成成功，但持久化失败：{exc}"

    return ok(response_data)


# ============================================================
# 用户感受报告（综合：反馈 + 对话 + 消费数据）
# ============================================================

@router.get("/api/admin/reports/user-sentiment")
@router.get("/admin/reports/user-sentiment")
def user_sentiment_report(
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    """综合用户感受报告：融合反馈评分、对话情感、消费满意度等多维度数据"""
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    # ---- 1. 反馈数据统计 ----
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT rating, content, type, created_at FROM feedbacks WHERE created_at >= %s ORDER BY created_at DESC",
            (start_date,),
        )
        feedback_rows = cursor.fetchall()

    fb_total = len(feedback_rows)
    fb_positive = sum(1 for r in feedback_rows if r["rating"] >= 4)
    fb_neutral = sum(1 for r in feedback_rows if r["rating"] == 3)
    fb_negative = sum(1 for r in feedback_rows if r["rating"] <= 2)
    fb_avg_rating = round(sum(r["rating"] for r in feedback_rows) / fb_total, 2) if fb_total else 0
    fb_satisfaction_pct = round(fb_positive / fb_total * 100) if fb_total else 0

    # 反馈分类统计
    type_stats = defaultdict(lambda: {"total": 0, "positive": 0, "negative": 0, "avg_rating": 0.0})
    for r in feedback_rows:
        tp = r["type"] or "其他"
        type_stats[tp]["total"] += 1
        type_stats[tp]["avg_rating"] += r["rating"]
        if r["rating"] >= 4:
            type_stats[tp]["positive"] += 1
        elif r["rating"] <= 2:
            type_stats[tp]["negative"] += 1

    feedback_categories = []
    for tp, st in sorted(type_stats.items(), key=lambda x: x[1]["total"], reverse=True):
        t = st["total"]
        feedback_categories.append({
            "name": tp,
            "total": t,
            "positive": st["positive"],
            "negative": st["negative"],
            "avgRating": round(st["avg_rating"] / t, 2) if t else 0,
            "satisfactionPct": round(st["positive"] / t * 100) if t else 0,
        })

    # 好评/差评典型案例
    positive_examples = [{"text": r["content"][:120], "rating": r["rating"], "date": str(r["created_at"])[:10]}
                         for r in feedback_rows if r["rating"] >= 4][:5]
    negative_examples = [{"text": r["content"][:120], "rating": r["rating"], "date": str(r["created_at"])[:10]}
                         for r in feedback_rows if r["rating"] <= 2][:5]

    # ---- 2. 对话情感分析 ----
    with db.cursor() as cursor:
        cursor.execute(
            "SELECT content, created_at FROM chat_records WHERE role='user' AND created_at >= %s ORDER BY created_at ASC",
            (start_date,),
        )
        chat_rows = cursor.fetchall()

    chat_counts = {"positive": 0, "neutral": 0, "negative": 0}
    daily_sentiment = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0, "total": 0})
    for row in chat_rows:
        text = row["content"] or ""
        label, _ = local_sentiment(text)
        day = str(row["created_at"])[:10]
        chat_counts[label] += 1
        daily_sentiment[day][label] += 1
        daily_sentiment[day]["total"] += 1

    chat_total = sum(chat_counts.values()) or 1
    chat_positive_ratio = round(chat_counts["positive"] / chat_total * 100)
    chat_neutral_ratio = round(chat_counts["neutral"] / chat_total * 100)
    chat_negative_ratio = round(chat_counts["negative"] / chat_total * 100)

    sentiment_trend = []
    for d in sorted(daily_sentiment.keys()):
        v = daily_sentiment[d]
        t = v["total"] or 1
        sentiment_trend.append({
            "date": d,
            "positive": round(v["positive"] / t * 100),
            "neutral": round(v["neutral"] / t * 100),
            "negative": round(v["negative"] / t * 100),
            "total": v["total"],
        })

    # ---- 3. 消费满意度数据（基于系统 ticket_orders 表）----
    consumption_breakdown = []
    consumption_avg_satisfaction = None
    consumption_total_revenue = 0
    consumption_avg_spend = 0
    consumption_record_count = 0
    with db.cursor() as cursor:
        cursor.execute("""
            SELECT COALESCE(SUM(total_amount), 0) AS total_revenue,
                   COALESCE(ROUND(AVG(total_amount * 1.0), 2), 0) AS avg_spend,
                   COUNT(*) AS record_count
            FROM ticket_orders WHERE order_status = 'paid'
        """)
        cons_row = cursor.fetchone()
        if cons_row:
            consumption_total_revenue = cons_row["total_revenue"] or 0
            consumption_avg_spend = cons_row["avg_spend"] or 0
            consumption_record_count = cons_row["record_count"] or 0

        cursor.execute("""
            SELECT t.ticket_type AS name,
                   COALESCE(SUM(o.total_amount), 0) AS amount
            FROM ticket_orders o
            JOIN tickets t ON t.id = o.ticket_id
            WHERE o.order_status = 'paid'
            GROUP BY t.ticket_type ORDER BY amount DESC
        """)
        cons_rows = cursor.fetchall()
        cons_total = sum(r["amount"] for r in cons_rows) or 1
        consumption_breakdown = [
            {"name": r["name"], "amount": r["amount"], "ratio": round(r["amount"] / cons_total * 100)}
            for r in cons_rows
        ]

        # 消费满意度取反馈表中的平均分作为参考
        cursor.execute("SELECT AVG(rating) AS avg_r FROM feedbacks WHERE type = '餐饮服务' OR type = '票务服务'")
        fb_cons = cursor.fetchone()
        if fb_cons and fb_cons["avg_r"]:
            consumption_avg_satisfaction = round(fb_cons["avg_r"], 1)
        else:
            consumption_avg_satisfaction = 4.0

    # ---- 4. 高频痛点提取 ----
    pain_point_keywords = {
        "排队等候": ["排队", "等了好久", "人多", "拥挤", "慢"],
        "网络信号": ["WiFi", "连不上", "信号", "卡", "网络"],
        "路线指引": ["迷路", "找不到", "指示牌", "导航", "怎么走"],
        "价格偏贵": ["太贵", "不值", "贵了", "性价比", "坑"],
        "无障碍设施": ["轮椅", "无障碍", "老人不便", "台阶", "电梯"],
        "语音交互": ["听不懂", "回答不准", "识别错误", "答非所问"],
    }
    all_feedback_text = " ".join(r["content"] or "" for r in feedback_rows)
    all_chat_text = " ".join(r["content"] or "" for r in chat_rows)
    combined_text = all_feedback_text + " " + all_chat_text

    pain_points = []
    for label, keywords in pain_point_keywords.items():
        score = sum(combined_text.count(kw) for kw in keywords)
        if score > 0:
            pain_points.append({"label": label, "score": score, "keywords": keywords})

    pain_points.sort(key=lambda x: x["score"], reverse=True)

    # ---- 5. 综合建议 ----
    suggestions = [
        "将高频问题补充进FAQ知识库，提升数字人回答命中率",
        "针对排队等候痛点，在数字人对话中增加实时人流提示和错峰建议",
        "优化景区WiFi覆盖，在信号盲区增加离线问答缓存功能",
        "在数字人回答中主动提供洗手间、餐饮、观光车等即时服务指引",
        "持续优化语音识别模型，提升方言和嘈杂环境下的识别准确率",
    ]
    if fb_satisfaction_pct < 80:
        suggestions.insert(0, f"当前满意度{fb_satisfaction_pct}%，建议重点关注低分反馈并逐一跟进改进")

    # ---- 6. 综合评分 ----
    chat_score = chat_positive_ratio * 0.4 + chat_neutral_ratio * 0.3 + chat_negative_ratio * 0.1
    feedback_score = fb_satisfaction_pct * 0.5 + (100 - fb_satisfaction_pct) * 0.2
    consumption_score = int(consumption_avg_satisfaction / 5 * 100) if consumption_avg_satisfaction else 75

    overall_score = round(chat_score * 0.3 + feedback_score * 0.4 + consumption_score * 0.3)

    # ---- 7. 组装返回 ----
    return ok({
        "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
        # 综合评分
        "overallScore": overall_score,
        "overallSummary": (
            f"近30天用户感受整体{'良好' if overall_score >= 70 else '一般' if overall_score >= 50 else '需关注'}，"
            f"综合满意度{overall_score}分。"
            f"反馈好评率{fb_satisfaction_pct}%，对话正向情绪占比{chat_positive_ratio}%。"
            f"{'建议重点关注负面反馈并持续改进服务。' if overall_score < 70 else '游客体验整体向好，建议持续优化。'}"
        ),
        # 反馈维度
        "feedback": {
            "total": fb_total,
            "positive": fb_positive,
            "neutral": fb_neutral,
            "negative": fb_negative,
            "avgRating": fb_avg_rating,
            "satisfactionPct": fb_satisfaction_pct,
            "categories": feedback_categories,
            "positiveExamples": positive_examples,
            "negativeExamples": negative_examples,
        },
        # 对话情感维度
        "chatSentiment": {
            "totalMessages": chat_total,
            "positiveRatio": chat_positive_ratio,
            "neutralRatio": chat_neutral_ratio,
            "negativeRatio": chat_negative_ratio,
            "trend": sentiment_trend,
        },
        # 消费满意度维度
        "consumption": {
            "available": consumption_record_count > 0,
            "avgSatisfaction": consumption_avg_satisfaction,
            "totalRevenue": consumption_total_revenue,
            "avgSpend": consumption_avg_spend,
            "recordCount": consumption_record_count,
            "costBreakdown": consumption_breakdown,
        },
        # 痛点分析
        "painPoints": pain_points[:6],
        # 改进建议
        "suggestions": suggestions,
        # 数据时间
        "generatedAt": datetime.now().isoformat(),
    })
