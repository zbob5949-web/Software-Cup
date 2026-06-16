"""管理后台 - 游客感受度报告接口。

接口编号：ADMIN-REPORT-01
用途：分析游客聊天文本的情感倾向，生成趋势、关注点和运营建议。
"""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends

from core.config import DEEPSEEK_KEY
from dependencies import get_current_admin_user, get_db
from routers.admin.common import extract_hot_keywords, ok
from services.chat_service import call_deepseek
from utils.response import Result

router = APIRouter()

POSITIVE_WORDS = {"喜欢", "满意", "不错", "很好", "好玩", "漂亮", "震撼", "方便", "推荐", "开心", "舒适", "赞"}
NEGATIVE_WORDS = {"差", "不满", "失望", "太贵", "排队", "拥挤", "找不到", "不好", "慢", "脏", "累", "投诉", "迷路"}


def local_sentiment(text: str) -> tuple[str, int]:
    """用本地正负向词典粗略判断单条游客消息情绪。"""
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos > neg:
        return "positive", pos - neg
    if neg > pos:
        return "negative", neg - pos
    return "neutral", 0


def ai_sentiment_summary(messages: list[str], counts: dict) -> dict | None:
    """可选调用 DeepSeek，把游客消息样本总结为结构化运营报告。"""
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


# ADMIN-REPORT-01：游客感受度报告接口，返回情绪趋势、样例、关注点和建议。
@router.get("/api/admin/reports/sentiment")
@router.get("/admin/reports/sentiment")
def sentiment_report(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    use_ai: bool = False,#是否使用DeepSeek增强分析（默认false）
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    """按时间范围分析用户消息情绪；use_ai=true时用 DeepSeek 增强总结。"""
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
        )#从 chat_records 表中查询指定时间范围内所有游客提问：
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

    # 持久化报告，补齐 sentiment_reports 表“建了但未使用”的问题。
    # 写库失败不影响前端查看实时报告。
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
