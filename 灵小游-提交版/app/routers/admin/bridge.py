"""
Admin Bridge Router — 适配 React 前端管理后台的 API 调用。
前端调用的端点与后端实际路由不一致，此文件提供中间适配层。
"""
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.dependencies import get_current_admin_user, get_db
from app.routers.admin.common import date_to_str, extract_hot_keywords, ok, semantic_cluster_questions
from app.routers.admin.schemas import KnowledgeTextForm
from app.services import dify_service
from app.services.chat_service import call_deepseek
from app.utils.faq_matcher import GENERIC_WORDS, LOCATION_WORDS
from app.utils.response import Result

router = APIRouter()

# ============================================================
# 1. Dashboard — GET /api/admin/dashboard
#    前端期望: { stats, hotQuestions, satisfaction, weather }
# ============================================================

@router.get("/api/admin/dashboard")
def bridge_dashboard(
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        # 统计卡片
        cursor.execute("""
            SELECT
              COUNT(DISTINCT CASE WHEN DATE(created_at)=CURDATE() THEN session_id END) AS today_sessions,
              COUNT(DISTINCT CASE WHEN YEARWEEK(created_at,1)=YEARWEEK(CURDATE(),1) THEN session_id END) AS week_sessions,
              COUNT(DISTINCT CASE WHEN DATE(created_at)=CURDATE() THEN COALESCE(phone, session_id) END) AS today_people,
              COUNT(DISTINCT CASE WHEN YEARWEEK(created_at,1)=YEARWEEK(CURDATE(),1) THEN COALESCE(phone, session_id) END) AS week_people
            FROM chat_records
            WHERE role = 'user'
        """)
        people = cursor.fetchone()

        stats = [
            {"title": "今日会话", "value": people["today_sessions"] if people else 0, "change": "今日", "changeType": "flat"},
            {"title": "本周会话", "value": people["week_sessions"] if people else 0, "change": "本周", "changeType": "up"},
            {"title": "今日活跃用户", "value": people["today_people"] if people else 0, "change": "今日", "changeType": "flat"},
            {"title": "本周活跃用户", "value": people["week_people"] if people else 0, "change": "本周", "changeType": "up"},
        ]

        # 热门问题 TOP5
        cursor.execute("""
            SELECT content FROM chat_records
            WHERE role = 'user' AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            ORDER BY created_at DESC LIMIT 1000
        """)
        recent = [r["content"] for r in cursor.fetchall()]
        clustered = semantic_cluster_questions(recent, 5)
        hot_questions = []
        for i, c in enumerate(clustered):
            hot_questions.append({
                "rank": i + 1,
                "question": c.get("semantic_label", c.get("question", "")),
                "count": c.get("count", 0),
            })

        # 满意度
        cursor.execute("SELECT rating, COUNT(*) AS cnt FROM feedbacks WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) GROUP BY rating")
        rating_rows = cursor.fetchall()
        positive = sum(r["cnt"] for r in rating_rows if r["rating"] >= 4)
        neutral = sum(r["cnt"] for r in rating_rows if r["rating"] == 3)
        negative = sum(r["cnt"] for r in rating_rows if r["rating"] <= 2)
        total = positive + neutral + negative or 1
        satisfaction = {
            "positive": round(positive / total * 100),
            "neutral": round(neutral / total * 100),
            "negative": round(negative / total * 100),
        }

    # 天气
    weather = {
        "location": "无锡灵山",
        "weather": "晴",
        "temp": "28°C",
        "humidity": "65%",
        "feels_like": "30°C",
        "advice": "适宜出游，注意防晒",
    }
    try:
        from app.services.weather_service import get_weather_data
        wd = get_weather_data()
        if wd and not wd.get("error"):
            weather = {
                "location": wd.get("city", "无锡灵山"),
                "weather": wd.get("weather", "晴"),
                "temp": wd.get("temperature", "28°C"),
                "humidity": wd.get("humidity", "65%"),
                "feels_like": wd.get("feels_like", wd.get("temperature", "28°C")),
                "advice": wd.get("advice", "适宜出游"),
            }
    except Exception:
        pass

    return ok({"stats": stats, "hotQuestions": hot_questions, "satisfaction": satisfaction, "weather": weather})


# ============================================================
# 2. Knowledge CRUD — 桥接到 faqs 表
#    前端用 title/content/category/status → 映射到 question/answer/category/is_active
# ============================================================

def _faq_to_knowledge(row) -> dict:
    status = "published" if bool(row.get("is_active")) else "draft"
    return {
        "id": str(row["id"]),
        "title": row.get("question", ""),
        "category": row.get("category") or "景点介绍",
        "status": status,
        "updatedAt": date_to_str(row.get("created_at")),
        "content": row.get("answer", ""),
    }


@router.get("/api/admin/knowledge")
def bridge_knowledge_list(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    where = ["1=1"]
    params = []
    if search:
        where.append("(question LIKE %s OR answer LIKE %s)")
        like = f"%{search}%"
        params.extend([like, like])
    if category:
        where.append("category = %s")
        params.append(category)
    with db.cursor() as cursor:
        cursor.execute(f"SELECT * FROM faqs WHERE {' AND '.join(where)} ORDER BY sort_order ASC, id DESC", params)
        rows = cursor.fetchall()
    return ok([_faq_to_knowledge(r) for r in rows])


@router.post("/api/admin/knowledge")
def bridge_knowledge_create(
    payload: dict,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    category = payload.get("category") or "景点介绍"
    status = payload.get("status", "draft")
    is_active = status == "published"
    if not title:
        return Result(400, "标题不能为空")
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO faqs (question, answer, category, keywords, is_active) VALUES (%s, %s, %s, %s, %s)",
                (title, content, category, title, is_active),
            )
            item_id = cursor.lastrowid
        db.commit()
        return ok({"id": item_id}, "知识条目创建成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"创建失败：{exc}")


@router.put("/api/admin/knowledge/{item_id}")
def bridge_knowledge_update(
    item_id: str,
    payload: dict,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        iid = int(item_id)
    except ValueError:
        return Result(400, "无效ID")
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    category = payload.get("category") or "景点介绍"
    status = payload.get("status", "draft")
    is_active = status == "published"
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "UPDATE faqs SET question=%s, answer=%s, category=%s, is_active=%s WHERE id=%s",
                (title, content, category, is_active, iid),
            )
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "知识条目不存在")
        db.commit()
        return ok({"id": iid}, "知识条目更新成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"更新失败：{exc}")


@router.delete("/api/admin/knowledge/{item_id}")
def bridge_knowledge_delete(
    item_id: str,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        iid = int(item_id)
    except ValueError:
        return Result(400, "无效ID")
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM faqs WHERE id = %s", (iid,))
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "知识条目不存在")
        db.commit()
        return ok({"id": iid}, "知识条目删除成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"删除失败：{exc}")


# ============================================================
# 3. Avatar / Digital Human Config — GET/PUT /api/admin/avatar
#    将前端的 avatar 字段映射到 digital_human_configs
# ============================================================

@router.get("/api/admin/avatar")
def bridge_avatar_get(
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM digital_human_configs WHERE is_active = TRUE ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
    except Exception:
        row = None

    if row:
        from app.services.digital_human_config import MODEL_CATALOG
        model_key = row.get("model_key", "live2d_haru")
        profile = MODEL_CATALOG.get(model_key, MODEL_CATALOG.get("live2d_haru", {}))
        avatar = {
            "name": row.get("name") or profile.get("label", "灵小游"),
            "welcomeMessage": f"你好，我是{row.get('name') or '灵小游'}，很高兴为您服务！",
            "introduction": row.get("appearance") or profile.get("appearance", "Live2D 数字人导游"),
            "videoUrl": f"/live2d/index.html?embed=1&model={profile.get('model_dir', 'Haru')}&api=http://127.0.0.1:8000",
            "voiceType": row.get("voice_name") or profile.get("default_voice", "zh-CN-XiaoyiNeural"),
            "speed": float(row.get("speed") or 1.0),
            "volume": float(row.get("volume") or 0.8),
            "updatedAt": date_to_str(row.get("updated_at")),
        }
    else:
        avatar = {
            "name": "灵小游",
            "welcomeMessage": "你好，我是灵小游，很高兴为您服务！",
            "introduction": "Live2D 数字人导游",
            "videoUrl": "/live2d/index.html?embed=1&model=Haru&api=http://127.0.0.1:8000",
            "voiceType": "zh-CN-XiaoyiNeural",
            "speed": 1.0,
            "volume": 0.8,
            "updatedAt": "",
        }
    return ok(avatar)


@router.put("/api/admin/avatar")
def bridge_avatar_update(
    payload: dict,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    name = (payload.get("name") or "").strip()
    voice = (payload.get("voice_type") or "").strip()
    welcome = (payload.get("welcome_message") or "").strip()
    intro = (payload.get("introduction") or "").strip()
    video = (payload.get("video_url") or "").strip()
    speed = float(payload.get("speed", 1.0))
    volume = float(payload.get("volume", 0.8))

    try:
        with db.cursor() as cursor:
            cursor.execute("SELECT id FROM digital_human_configs WHERE is_active = TRUE LIMIT 1")
            row = cursor.fetchone()
            if row:
                fields = []
                params = []
                if name:
                    fields.append("name = %s")
                    params.append(name)
                if voice:
                    fields.append("voice_name = %s")
                    params.append(voice)
                if intro:
                    fields.append("appearance = %s")
                    params.append(intro)
                if speed is not None:
                    fields.append("speed = %s")
                    params.append(speed)
                if volume is not None:
                    fields.append("volume = %s")
                    params.append(volume)
                if fields:
                    cursor.execute(f"UPDATE digital_human_configs SET {', '.join(fields)} WHERE id = %s", params + [row["id"]])
        db.commit()
        return ok(None, "数字人配置更新成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"更新失败：{exc}")


# ============================================================
# 4. Feedback — GET /api/admin/feedback, DELETE /api/admin/feedback/:id
# ============================================================

@router.get("/api/admin/feedback")
def bridge_feedback_list(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    rating: Optional[int] = Query(None),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    where = ["1=1"]
    params = []
    if search:
        where.append("(content LIKE %s)")
        params.append(f"%{search}%")
    if category:
        where.append("type = %s")
        params.append(category)
    if rating is not None:
        where.append("rating = %s")
        params.append(rating)

    with db.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS cnt FROM feedbacks WHERE {' AND '.join(where)}", params)
        total = cursor.fetchone()["cnt"]
        cursor.execute(
            f"""SELECT id, phone, type, rating, content, status, created_at
                FROM feedbacks WHERE {' AND '.join(where)} ORDER BY created_at DESC""",
            params,
        )
        rows = cursor.fetchall()

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "username": r.get("phone") or "游客",
            "date": date_to_str(r.get("created_at")),
            "rating": r.get("rating", 5),
            "content": r.get("content", ""),
            "category": r.get("type") or "其他",
        })

    positive = sum(1 for r in rows if r.get("rating", 0) >= 4)
    neutral = sum(1 for r in rows if r.get("rating", 0) == 3)
    negative = sum(1 for r in rows if r.get("rating", 0) <= 2)
    avg_rating = round(sum(r.get("rating", 0) for r in rows) / len(rows), 2) if rows else 0

    stats = {"total": total, "positive": positive, "neutral": neutral, "negative": negative, "avg_rating": avg_rating}
    return ok({"items": items, "stats": stats})


@router.delete("/api/admin/feedback/{item_id}")
def bridge_feedback_delete(
    item_id: str,
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    try:
        iid = int(item_id)
    except ValueError:
        return Result(400, "无效ID")
    try:
        with db.cursor() as cursor:
            cursor.execute("DELETE FROM feedbacks WHERE id = %s", (iid,))
            if cursor.rowcount == 0:
                db.rollback()
                return Result(404, "反馈不存在")
        db.commit()
        return ok({"id": iid}, "反馈删除成功")
    except Exception as exc:
        db.rollback()
        return Result(500, f"删除失败：{exc}")


# ============================================================
# 5. Statistics — GET /api/admin/statistics?days=7|30
#    返回: { kpis, trend, hotQuestions, sourceRatio, satisfactionTrend, sentimentTrend, sentimentSummary, sentimentKeywords }
# ============================================================

@router.get("/api/admin/statistics")
def bridge_statistics(
    days: int = Query(7, ge=1, le=90),
    _: dict = Depends(get_current_admin_user),
    db=Depends(get_db),
):
    with db.cursor() as cursor:
        # KPI
        cursor.execute(f"""
            SELECT
              COUNT(DISTINCT session_id) AS total_sessions,
              COUNT(*) AS total_messages
            FROM chat_records
            WHERE role='user' AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
        """, (days,))
        kpi_row = cursor.fetchone()
        total_sessions = kpi_row["total_sessions"] if kpi_row else 0
        total_messages = kpi_row["total_messages"] if kpi_row else 0
        cursor.execute("SELECT COUNT(*) AS cnt, COUNT(DISTINCT phone) AS people FROM favorites WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)", (days,))
        favorite_row = cursor.fetchone() or {}
        favorite_count = int(favorite_row.get("cnt") or 0)
        favorite_people = int(favorite_row.get("people") or 0)
        cursor.execute("SELECT COUNT(*) AS cnt, AVG(rating) AS avg_rating FROM feedbacks WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)", (days,))
        feedback_row = cursor.fetchone() or {}
        feedback_count = int(feedback_row.get("cnt") or 0)
        feedback_satisfaction = round(float(feedback_row.get("avg_rating") or 0) / 5 * 100) if feedback_count else 0
        cursor.execute("SELECT content FROM feedbacks WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY) AND content IS NOT NULL ORDER BY created_at DESC LIMIT 2000", (days,))
        feedback_texts = [row["content"] for row in cursor.fetchall()]

        kpis = [
            {"title": "服务人次", "value": total_sessions, "change": f"近{days}天", "changeType": "up"},
            {"title": "交互消息", "value": total_messages, "change": f"近{days}天", "changeType": "up"},
            {"title": "用户收藏", "value": favorite_count, "change": f"{favorite_people}位用户", "changeType": "up"},
            {"title": "用户满意度", "value": f"{feedback_satisfaction}%", "change": f"{feedback_count}条反馈", "changeType": "up" if feedback_satisfaction >= 60 else "flat"},
        ]

        # 日趋势
        cursor.execute(f"""
            SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM chat_records WHERE role='user' AND created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(created_at) ORDER BY day ASC
        """, (days,))
        trend = [{"date": date_to_str(r["day"]), "count": r["cnt"]} for r in cursor.fetchall()]

        # 热门问题 TOP10
        cursor.execute("""
            SELECT content FROM chat_records WHERE role='user' ORDER BY created_at DESC LIMIT 2000
        """)
        recent = [r["content"] for r in cursor.fetchall()]
        clustered = semantic_cluster_questions(recent, 10)
        hot_questions = []
        for i, c in enumerate(clustered):
            hot_questions.append({
                "rank": i + 1,
                "question": c.get("semantic_label", c.get("question", "")),
                "count": c.get("count", 0),
            })

        # 来源分布
        cursor.execute(f"""
            SELECT COALESCE(source, 'unknown') AS src, COUNT(*) AS cnt
            FROM chat_records WHERE role='assistant' AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY COALESCE(source, 'unknown')
        """, (days,))
        source_rows = cursor.fetchall()
        source_total = sum(r["cnt"] for r in source_rows) or 1
        source_colors = {"faq": "#18A999", "dify": "#4F7CFF", "local": "#F0C48A", "ai": "#D6A84F", "weather": "#818CF8"}
        source_ratio = []
        for r in source_rows:
            src = r["src"]
            source_ratio.append({
                "name": src,
                "value": round(r["cnt"] / source_total * 100),
                "color": source_colors.get(src, "#A0AEC0"),
            })

        # 满意度趋势
        cursor.execute(f"""
            SELECT DATE(created_at) AS day, AVG(rating) AS avg_r, COUNT(*) AS cnt
            FROM feedbacks WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(created_at) ORDER BY day ASC
        """, (days,))
        satisfaction_trend = [
            {"date": date_to_str(r["day"]), "satisfaction": round(float(r["avg_r"] or 0) / 5 * 100), "count": r["cnt"]}
            for r in cursor.fetchall()
        ]

    # 情感关键词（基于最近问题提取）
    positive_words = {"喜欢", "满意", "不错", "很好", "好玩", "漂亮", "震撼", "方便", "推荐", "开心"}
    negative_words = {"差", "不满", "失望", "太贵", "排队", "拥挤", "找不到", "不好", "慢", "脏"}
    pos_counter = {}
    neg_counter = {}
    for q in feedback_texts[:200]:
        for w in positive_words:
            if w in q: pos_counter[w] = pos_counter.get(w, 0) + 1
        for w in negative_words:
            if w in q: neg_counter[w] = neg_counter.get(w, 0) + 1
    pos_keywords = sorted(pos_counter, key=pos_counter.get, reverse=True)[:10]
    neg_keywords = sorted(neg_counter, key=neg_counter.get, reverse=True)[:10]

    # 情感趋势（模拟 + 实际混合）
    sentiment_trend = []
    end_date = date.today()
    pos_count = pos_count_total = 0
    neg_count = neg_count_total = 0
    neutral_count = neutral_count_total = 0
    for i in range(days):
        d = end_date - timedelta(days=days - 1 - i)
        day_pos = len([1 for q in feedback_texts if any(w in q for w in positive_words)])
        day_neg = len([1 for q in feedback_texts if any(w in q for w in negative_words)])
        day_neu = len(feedback_texts) // days - day_pos - day_neg
        day_pos = max(0, day_pos); day_neg = max(0, day_neg); day_neu = max(0, day_neu)
        pos_count_total += day_pos; neg_count_total += day_neg; neutral_count_total += day_neu
        total_day = day_pos + day_neg + day_neu or 1
        sentiment_trend.append({
            "date": d.isoformat(),
            "positive": round(day_pos / total_day * 100),
            "neutral": round(day_neu / total_day * 100),
            "negative": round(day_neg / total_day * 100),
            "avgScore": round((day_pos * 2 + day_neu * 1 + day_neg * 0) / total_day, 2),
        })

    sentiment_total = pos_count_total + neg_count_total + neutral_count_total or 1
    sentiment_summary = {
        "totalAnalyzed": sentiment_total,
        "positiveRatio": round(pos_count_total / sentiment_total * 100),
        "neutralRatio": round(neutral_count_total / sentiment_total * 100),
        "negativeRatio": round(neg_count_total / sentiment_total * 100),
        "avgSentimentScore": round((pos_count_total * 2 + neutral_count_total) / sentiment_total, 2),
        "positiveTrend": "稳定",
        "trend": "flat",
    }

    return ok({
        "kpis": kpis,
        "trend": trend,
        "hotQuestions": hot_questions,
        "sourceRatio": source_ratio,
        "satisfactionTrend": satisfaction_trend,
        "sentimentTrend": sentiment_trend,
        "sentimentSummary": sentiment_summary,
        "sentimentKeywords": {
            "positive": pos_keywords,
            "negative": neg_keywords,
        },
    })


# ============================================================
# 6. Settings — GET /api/admin/settings, PUT /api/admin/settings/system, PUT /api/admin/settings/api
#    使用本地 JSON 文件持久化
# ============================================================

_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "admin_settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "systemInfo": {"systemName": "灵山景区导览系统", "contactPhone": "", "contactEmail": "", "copyright": "", "beian": ""},
        "apiConfig": {"weatherApi": "", "weatherKey": "", "llmApi": "https://api.deepseek.com/v1", "llmModel": "deepseek-chat", "dbHost": "localhost", "dbPort": "3306", "dbName": "scenic_guide_db", "dbUser": "root", "dbPassword": ""},
    }


def _save_settings(data: dict):
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.get("/api/admin/settings")
def bridge_settings_get(_: dict = Depends(get_current_admin_user)):
    return ok(_load_settings())


@router.put("/api/admin/settings/system")
def bridge_settings_system(payload: dict, _: dict = Depends(get_current_admin_user)):
    settings = _load_settings()
    settings["systemInfo"] = {
        "systemName": payload.get("system_name", settings["systemInfo"]["systemName"]),
        "contactPhone": payload.get("contact_phone", settings["systemInfo"]["contactPhone"]),
        "contactEmail": payload.get("contact_email", settings["systemInfo"]["contactEmail"]),
        "copyright": payload.get("copyright", settings["systemInfo"]["copyright"]),
        "beian": payload.get("beian", settings["systemInfo"]["beian"]),
    }
    _save_settings(settings)
    return ok(None, "系统设置更新成功")


@router.put("/api/admin/settings/api")
def bridge_settings_api(payload: dict, _: dict = Depends(get_current_admin_user)):
    settings = _load_settings()
    settings["apiConfig"] = {
        "weatherApi": payload.get("weather_api", settings["apiConfig"]["weatherApi"]),
        "weatherKey": payload.get("weather_key", settings["apiConfig"]["weatherKey"]),
        "llmApi": payload.get("llm_api", settings["apiConfig"]["llmApi"]),
        "llmModel": payload.get("llm_model", settings["apiConfig"]["llmModel"]),
        "dbHost": payload.get("db_host", settings["apiConfig"]["dbHost"]),
        "dbPort": payload.get("db_port", settings["apiConfig"]["dbPort"]),
        "dbName": payload.get("db_name", settings["apiConfig"]["dbName"]),
        "dbUser": payload.get("db_user", settings["apiConfig"]["dbUser"]),
        "dbPassword": payload.get("db_password", settings["apiConfig"]["dbPassword"]),
    }
    _save_settings(settings)
    return ok(None, "接口配置更新成功")
