"""
聊天路由：AI 对话、历史记录
支持正式用户（完整功能）和游客（每日限额对话）
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.database import get_db_connection
from app.dependencies import get_db, get_current_user, get_current_user_optional, get_user_identity
from app.utils.response import Result
from app.services import chat_service
from app.services.weather_service import format_weather_reply, get_weather_data, is_weather_query
from app.core.config import GUEST_DAILY_CHAT_LIMIT

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None   # 可不传，自动生成


class DetailRequest(BaseModel):
    session_id: str


def _fallback_chat_reply(question: str) -> tuple[str, str]:
    """数据库不可用时给游客端兜底，真实知识库可用时不会走这里。"""
    if any(word in question for word in ["你好", "您好", "你是谁", "介绍"]):
        return (
            "你好，我是灵小游，灵山景区的智能导览助手。你可以问我景点介绍、演出时间、路线推荐、门票开放时间和服务设施位置。",
            "fallback",
        )
    if any(word in question for word in ["路线", "推荐", "规划", "游玩", "游览"]):
        return (
            "如果第一次来灵山，建议按“九龙灌浴、灵山大佛、梵宫、五印坛城”的顺序游览。这样能兼顾标志性景观、文化讲解和路线效率；如果你偏向历史文化或亲子游，我可以继续细化路线。",
            "fallback",
        )
    if any(word in question for word in ["灵山大佛", "大佛"]):
        return (
            "灵山大佛是灵山胜境的代表性景观，为露天青铜释迦牟尼立像。游览时可以沿登云道上行，到佛脚平台近距离参观，并俯瞰太湖方向景色。",
            "fallback",
        )
    if any(word in question for word in ["梵宫", "吉祥颂"]):
        return (
            "灵山梵宫以佛教文化艺术和大型室内空间见长，内部有穹顶、壁画、木雕等艺术展示，也是《灵山吉祥颂》等演出的重要场所。演出时间建议以景区当天公告为准。",
            "fallback",
        )
    if any(word in question for word in ["九龙灌浴", "演出", "表演"]):
        return (
            "九龙灌浴是灵山胜境的标志性动态景观，适合提前到场观看。具体演出场次可能会因节假日和天气调整，建议以景区广播或当天公告为准。",
            "fallback",
        )
    if any(word in question for word in ["门票", "开放", "时间", "购票"]):
        return (
            "门票价格和开放时间会随季节、节假日和活动调整，建议以景区官方当天公告为准。热门日期建议提前线上购票，并预留入园和观演排队时间。",
            "fallback",
        )
    return (
        "这个问题我会按灵山景区导览来理解。你可以继续告诉我想了解的景点、游览时长或兴趣偏好，我会帮你做更具体的讲解和路线建议。",
        "fallback",
    )


def _check_guest_chat_quota(cursor, guest_id: str) -> tuple[bool, int, int]:
    """
    检查游客今日对话额度
    返回 (是否允许继续, 今日已用次数, 每日限额)
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cursor.execute(
        """SELECT COUNT(*) FROM chat_records
           WHERE phone = %s AND role = 'user' AND created_at >= %s""",
        (guest_id, today_start)
    )
    row = cursor.fetchone()
    used = row["COUNT(*)"] if isinstance(row, dict) else row[0]
    remaining = max(0, GUEST_DAILY_CHAT_LIMIT - used)
    return (used < GUEST_DAILY_CHAT_LIMIT, used, GUEST_DAILY_CHAT_LIMIT)


# ---------- AI 对话 ----------
@router.post("/api/user/chat")
def chat(
    req: ChatRequest,
    phone: str = Depends(get_current_user_optional),
    identity: dict = Depends(get_user_identity),
):
    """用户/游客发送消息，返回智能回复"""
    question = req.question.strip()
    if not question:
        return Result(400, "问题不能为空")

    session_id = req.session_id or uuid.uuid4().hex
    db = get_db_connection()
    if not db:
        # 数据库不可用时：仍然走 Dify 知识库 + DeepSeek，不做硬编码兜底
        result = chat_service.process_user_chat_without_db(question)
        return Result(200, "success", {
            "reply": result["reply"],
            "source": result["source"],
            "session_id": session_id,
        })

    # 确定用户标识
    if identity["type"] == "user":
        user_id = identity["id"]   # 手机号
        user_label = user_id
    elif identity["type"] == "guest":
        user_id = identity["id"]    # guest_xxx
        user_label = user_id
    else:
        # 完全匿名：生成临时标识（无法持久化，仅本次对话可用）
        user_id = f"anon_{uuid.uuid4().hex[:8]}"
        user_label = None

    try:
        cursor = db.cursor()

        # 游客每日配额检查（只查一次，结果复用）
        guest_quota = None
        if identity["type"] == "guest":
            allowed, used, limit = _check_guest_chat_quota(cursor, user_id)
            guest_quota = {"used": used, "limit": limit, "remaining": max(0, limit - used)}
            if not allowed:
                return Result(
                    42902,
                    f"游客每日对话额度已用完（{used}/{limit}），请明天再试或注册登录享受无限次对话"
                )

        # 1. 保存用户消息
        chat_service.save_message(cursor, session_id, user_id, "user", question, "user_input")

        # 2. 天气类问题直接联动天气接口
        if is_weather_query(question):
            weather_data = get_weather_data()
            reply = format_weather_reply(weather_data)
            source = "weather"
        else:
            result = chat_service.process_user_chat(cursor, question, session_id, user_id)
            reply = result["reply"]
            source = result["source"]

        # 3. 保存机器人回复
        chat_service.save_message(cursor, session_id, user_id, "assistant", reply, source)

        # 4. 清理会话旧记录
        chat_service.cleanup_old_records(cursor, session_id)

        db.commit()

        response_data = {
            "reply": reply,
            "source": source,
            "session_id": session_id,
        }

        # 游客附加配额信息（使用缓存结果）
        if guest_quota:
            response_data["quota"] = guest_quota

        return Result(200, "success", response_data)

    except Exception as e:
        db.rollback()
        print(f"[chat error] {e}")
        return Result(500, f"处理失败：{str(e)}")
    finally:
        db.close()


# ---------- 历史会话列表 ----------
@router.get("/api/user/history")
def history(
    identity: dict = Depends(get_user_identity),
    db=Depends(get_db)
):
    """
    已登录用户的历史会话列表
    游客不可查看历史记录
    """
    if identity["type"] == "guest":
        return Result(40301, "游客模式下无法查看历史记录，请注册登录后使用")
    if identity["type"] == "anonymous":
        return Result(401, "请先登录")

    phone = identity["id"]
    cursor = db.cursor()
    sessions = chat_service.get_user_sessions(cursor, phone)
    return Result(200, "success", sessions)


# ---------- 会话详情 ----------
@router.get("/api/user/chat/detail")
def chat_detail(
    session_id: str,
    identity: dict = Depends(get_user_identity),
    db=Depends(get_db)
):
    """
    查看指定会话的所有消息
    游客不可查看历史详情
    """
    if identity["type"] == "guest":
        return Result(40301, "游客模式下无法查看历史记录，请注册登录后使用")
    if identity["type"] == "anonymous":
        return Result(401, "请先登录")

    phone = identity["id"]
    cursor = db.cursor()
    messages = chat_service.get_session_messages(cursor, session_id, phone)
    if not messages:
        return Result(404, "会话不存在")
    return Result(200, "success", messages)
