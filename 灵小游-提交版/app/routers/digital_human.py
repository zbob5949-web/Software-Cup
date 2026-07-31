import math
import os
import re
import uuid
import heapq
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from app.database import get_db_connection
from app.dependencies import get_current_user_optional, get_user_identity
from app.services import chat_service
from app.services.digital_human_config import MODEL_CATALOG, DEFAULT_MODEL_KEY, get_active_profile, get_model_profile
from app.services.weather_service import format_weather_reply, get_weather_data, is_weather_query
from app.utils.response import Result


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[1]
DIGITAL_HUMAN_DIR = BASE_DIR / "digital_human" / "live2d_host"



class DigitalHumanChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    location: dict | None = None
    active_route_id: str | None = None
    user_interests: list[str] = []


class MapLiveRouteRequest(BaseModel):
    latitude: float
    longitude: float
    target_spot_id: int | None = None
    target_name: str | None = None


INTEREST_TO_PLAN_KEYWORDS = {
    "入门": ["入门", "休闲", "首次", "第一次", "精华"],
    "轻松": ["亲子", "家庭", "儿童", "老人", "轻松", "祈福"],
    "普通": ["自然", "风光", "摄影", "太湖", "慢游"],
    "深度": ["历史", "文化", "佛教", "艺术", "深度"],
}


FALLBACK_KNOWLEDGE = [
    (
        re.compile(r"路线|怎么走|推荐|游玩|游览|历史|自然|亲子|规划"),
        "relaxed",
        "explain",
        "如果你第一次来，我推荐先看九龙灌浴，再到灵山大佛，随后游览梵宫和五印坛城。喜欢历史文化的游客可以重点听佛教文化与建筑故事，喜欢自然风光的游客可以多停留在太湖视野和广场区域。",
    ),
    (
        re.compile(r"门票|价格|购票|开放|时间"),
        "relaxed",
        "explain",
        "门票和开放时间会随节假日调整，建议以景区当天公告为准。通常可以提前在线购票，到达后按预约时段入园，热门演出建议提前到场。",
    ),
    (
        re.compile(r"梵宫|灵山大佛|九龙灌浴|五印坛城|祥符禅寺|景点"),
        "happy",
        "point",
        "灵山大佛是景区代表性景观，气势庄严；梵宫以精美建筑和文化展示见长；九龙灌浴适合观看动态演出；五印坛城适合了解藏传佛教艺术。",
    ),
    (
        re.compile(r"你好|您好|在吗|介绍|你是谁"),
        "happy",
        "welcome",
        "你好，我是灵小游，灵山景区的智能数字人导游。我可以用语音、表情和动作为你讲解景点、推荐路线，也可以回答门票、演出、交通和服务设施问题。",
    ),
    (
        re.compile(r"天气|下雨|热|冷|阴|晴"),
        "relaxed",
        "alert",
        "天气会影响游览体验。若遇到下雨，建议优先安排梵宫等室内区域；天气晴好时，可以把灵山大佛和广场区域放在上午或傍晚游览。",
    ),
    (
        re.compile(r"厕所|餐厅|停车|服务|出口|入口"),
        "relaxed",
        "point",
        "停车、餐饮、卫生间和游客中心通常分布在入口、主要广场和核心景点附近。你可以告诉我当前位置，我会继续帮你规划最近的服务点。",
    ),
]


EMOTION_RULES = {
    "sad": [
        (re.compile(r"抱歉|不好意思|对不起|遗憾|可惜|很遗憾"), 3),
        (re.compile(r"无法|不能|没办法|未能|失败|出错|异常|暂无"), 3),
        (re.compile(r"关闭|停运|停业|暂停|取消"), 2),
    ],
    "surprised": [
        (re.compile(r"竟然|居然|没想到|真没想到|原来"), 3),
        (re.compile(r"注意|特别注意|务必|千万|警告|紧急|突发"), 2),
        (re.compile(r"震撼|壮观|惊人|非常罕见"), 2),
    ],
    "relaxed": [
        (re.compile(r"建议|推荐|可以先|不妨|可以考虑|通常|一般"), 3),
        (re.compile(r"如果|根据|按照|适合|安排|规划|优先"), 2),
        (re.compile(r"天气|下雨|晴好|路线|游览|步行|到达"), 2),
    ],
    "happy": [
        (re.compile(r"欢迎|你好|您好|很高兴|当然可以|没问题"), 3),
        (re.compile(r"精彩|精美|壮观|宏伟|绝佳|非常适合|值得"), 2),
        (re.compile(r"祝你|祝您|玩得开心|旅途愉快|不容错过"), 3),
    ],
    "angry": [
        (re.compile(r"严禁|禁止|不得|请勿|不要"), 3),
        (re.compile(r"违规|违法|危险行为"), 2),
    ],
}


GESTURE_RULES = {
    "alert": re.compile(r"注意|提醒|警告|务必|天气|下雨|调整|突发"),
    "soft": re.compile(r"抱歉|遗憾|无法|不能|失败|暂无"),
    "point": re.compile(r"路线|先到|随后|然后|前往|入口|出口|附近|位置|怎么走"),
    "explain": re.compile(r"介绍|因为|代表|历史|文化|意思是|建议|通常|一般"),
    "welcome": re.compile(r"你好|您好|欢迎|我是|很高兴为你服务"),
}


REPLY_TYPE_RULES = [
    ("apology", re.compile(r"抱歉|遗憾|无法|不能|失败|暂无|未开放|取消")),
    ("notice", re.compile(r"注意|提醒|务必|请勿|禁止|天气|下雨|高峰|预约")),
    ("recommend", re.compile(r"建议|推荐|可以先|不妨|适合|路线|游览|安排")),
    ("welcome", re.compile(r"你好|您好|欢迎|我是|很高兴为你服务")),
    ("explain", re.compile(r"介绍|因为|代表|历史|文化|由来|意思|特点|看点")),
]


def _score_emotion(text: str) -> dict[str, int]:
    scores = {name: 0 for name in EMOTION_RULES}
    for emotion, rules in EMOTION_RULES.items():
        for pattern, weight in rules:
            if pattern.search(text):
                scores[emotion] += weight
    return scores


def _detect_reply_type(text: str, emotion: str) -> str:
    for reply_type, pattern in REPLY_TYPE_RULES:
        if pattern.search(text):
            return reply_type
    if emotion == "sad":
        return "apology"
    if emotion == "surprised":
        return "notice"
    if emotion == "relaxed":
        return "recommend"
    if emotion == "happy":
        return "explain"
    return "explain"


def _normalize_reply_tone(reply: str) -> str:
    text = re.sub(r"\s+", " ", (reply or "").strip())
    if not text:
        return text

    # 去掉过于生硬的客服口吻前缀
    text = re.sub(r"^(您好[！!，,]?|你好[！!，,]?|亲[，,]?|游客朋友[，,]?)+", "", text).strip()
    text = re.sub(r"^(为您推荐|建议您|建议可以|温馨提示[:：]?)", "", text).strip()

    # 用更像导游口播的衔接词
    text = text.replace("您可以", "可以")
    text = text.replace("建议您", "建议")
    text = text.replace("为您", "")

    # 按句子拆分，保留完整语义；知识库回答可能较长，放宽到 280 字 / 前 5 句
    parts = re.split(r"(?<=[。！？!?])", text)
    merged = "".join(part for part in parts if part).strip()
    if len(merged) > 280 and len(parts) >= 5:
        merged = "".join(parts[:5]).strip()
    elif len(merged) > 200 and len(parts) >= 3:
        merged = "".join(parts[:3]).strip()

    if not re.search(r"[。！？!?]$", merged):
        merged += "。"
    return merged


def _clean_display_text(text: str) -> str:
    """去掉回复中的 markdown 标记、emoji 和后台术语，适合朗读和展示"""
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`{1,3}', '', text)
    text = re.sub(r'[\U0001F000-\U0001FFFF☀-➿︀-️]', '', text)
    text = re.sub(r'[⌚-⏳■-◿☀-⛿✂-➰]', '', text)
    # 移除后台术语，用自然导游口吻替代
    text = re.sub(r'根据?知识库[^，。,！？!?]*[，。！？!?]', '', text)
    text = re.sub(r'知识库[中内]?[^，。,！？!?]*[，。！？!?]', '', text)
    text = re.sub(r'资料库[中内]?[^，。,！？!?]*[，。！？!?]', '', text)
    text = re.sub(r'数据库[中内]?[^，。,！？!?]*[，。！？!?]', '', text)
    text = re.sub(r'系统提示[^，。,！？!?]*[，。！？!?]', '', text)
    return text.strip()


def _shape_digital_human_reply(reply: str, emotion: str) -> str:
    text = _normalize_reply_tone(reply)
    if not text:
        return text

    reply_type = _detect_reply_type(text, emotion)

    if reply_type == "welcome" and not re.search(r"你好|欢迎|很高兴", text):
        text = "你好，我来给你介绍一下，" + text
    elif reply_type == "recommend" and not re.search(r"建议|可以先|不妨|适合", text):
        text = "建议这样安排，" + text
    elif reply_type == "notice" and not re.search(r"注意|提醒|务必|请留意", text):
        text = "这里提醒你一下，" + text
    elif reply_type == "apology" and not re.search(r"抱歉|遗憾", text):
        text = "抱歉，" + text
    elif reply_type == "explain" and not re.search(r"可以这样理解|这处景点|这里的意思是|这段内容很值得听一听", text):
        text = "这段内容很值得听一听，" + text

    return text


def _detect_emotion(text: str, user_interests: list[str] | None = None,
                    user_question: str | None = None) -> str:
    # 基础分数：从 AI 回复文本中匹配情绪关键词
    scores = _score_emotion(text)

    # 用户偏好标签 → 情感倾向加权（软影响，每项仅 +1）
    if user_interests:
        interest_emotion_map = {
            "亲子": "happy",
            "美食": "happy",
            "祈福": "relaxed",
            "历史": "relaxed",
            "自然": "relaxed",
            "摄影": "relaxed",
        }
        for interest in user_interests:
            emotion = interest_emotion_map.get(interest)
            if emotion:
                scores[emotion] = scores.get(emotion, 0) + 1

    # 用户问题语境分析（用户情绪倾向）
    if user_question:
        if re.search(r'着急|紧急|怎么办|快|来不及|找不到|迷路', user_question):
            scores["relaxed"] = scores.get("relaxed", 0) + 2
        if re.search(r'太好了|真棒|好期待|第一次|终于|开心|推荐|想去', user_question):
            scores["happy"] = scores.get("happy", 0) + 2
        if re.search(r'可惜|遗憾|失望|关门|取消了|下雨', user_question):
            scores["sad"] = scores.get("sad", 0) + 1
            scores["relaxed"] = scores.get("relaxed", 0) + 1

    order = ["sad", "surprised", "angry", "relaxed", "happy"]
    best_emotion = "neutral"
    best_score = 1
    for emotion in order:
        score = scores.get(emotion, 0)
        if score > best_score:
            best_emotion = emotion
            best_score = score
    return best_emotion


def _detect_gesture(text: str, emotion: str) -> str:
    if emotion == "surprised":
        return "alert"
    if emotion == "sad":
        return "soft"
    for gesture, pattern in GESTURE_RULES.items():
        if pattern.search(text):
            return gesture
    return "welcome" if emotion == "happy" else "idle"


def _fallback_reply(question: str) -> dict:
    for pattern, emotion, gesture, reply in FALLBACK_KNOWLEDGE:
        if pattern.search(question):
            return {
                "reply": reply,
                "emotion": emotion,
                "gesture": gesture,
                "source": "digital_human_fallback",
            }
    reply = (
        "我先按景区导览场景给你建议：如果时间充足，可以按核心景点、文化建筑、休息服务点的顺序游览。"
        "如果你告诉我兴趣偏好，比如历史文化、自然风光或亲子游，我可以继续给你定制路线。"
    )
    return {
        "reply": reply,
        "emotion": "relaxed",
        "gesture": "explain",
        "source": "digital_human_fallback",
    }


@router.post("/api/digital-human/chat")
def digital_human_chat(
    req: DigitalHumanChatRequest,
    authorization: str = Header(None),
):
    question = req.question.strip()
    if not question:
        return Result(400, "问题不能为空")

    # 识别用户身份
    identity = get_user_identity(authorization)
    if identity["type"] == "user":
        user_id = identity["id"]  # 手机号
    elif identity["type"] == "guest":
        user_id = identity["id"]  # guest_xxx
    else:
        user_id = f"anon_{uuid.uuid4().hex[:8]}"

    session_id = req.session_id or uuid.uuid4().hex
    conn = get_db_connection()
    if not conn:
        data = _fallback_reply(question)
        data["session_id"] = session_id
        return Result(200, "success", data)

    try:
        cursor = conn.cursor()

        # 先判断是否为导航请求（导航不纳入会话管理，不保存聊天记录）
        nav_reply = None
        if not is_weather_query(question):
            nav_reply = _build_navigation_reply(question, req.location, req.active_route_id, cursor)
        if nav_reply:
            data = nav_reply
            data["session_id"] = session_id
            conn.commit()
            return Result(200, "success", data)

        # 以下是真正的对话请求：保存用户消息
        chat_service.save_message(cursor, session_id, user_id, "user", question, "user_input")

        if is_weather_query(question):
            weather_data = get_weather_data()
            reply = format_weather_reply(weather_data)
            source = "weather"
        else:
            result = chat_service.process_user_chat(cursor, question, session_id, user_id)
            reply = result["reply"]
            source = result["source"]
            if any(flag in reply for flag in ("服务异常", "请重试", "暂时不可用", "不可用", "未配置")):
                faq_matches = chat_service.match_faq(cursor, question)
                if faq_matches:
                    reply = faq_matches[0]["answer"]
                    source = "faq_fallback"
        emotion = _detect_emotion(reply, user_interests=req.user_interests, user_question=question)
        reply = _shape_digital_human_reply(reply, emotion)
        reply = _clean_display_text(reply)
        emotion = _detect_emotion(reply, user_interests=req.user_interests, user_question=question)

        # 保存 AI 回复
        chat_service.save_message(cursor, session_id, user_id, "assistant", reply, source)
        chat_service.cleanup_old_records(cursor, session_id)
        conn.commit()

        return Result(
            200,
            "success",
            {
                "reply": reply,
                "source": source,
                "session_id": session_id,
                "emotion": emotion,
                "gesture": _detect_gesture(reply, emotion),
            },
        )
    except Exception:
        # 异常时也尝试 FAQ 匹配，不直接给模糊回答
        try:
            from app.services.chat_service import match_faq
            faq = match_faq(cursor, question)
            if faq and faq[0].get("score", 0) >= 80:
                reply = faq[0]["answer"]
                source = "faq"
            else:
                data = _fallback_reply(question)
                reply = data["reply"]
                source = data["source"]
        except Exception:
            data = _fallback_reply(question)
            reply = data["reply"]
            source = data["source"]
        emotion = _detect_emotion(reply, user_interests=req.user_interests, user_question=question)
        reply = _shape_digital_human_reply(reply, emotion)
        return Result(200, "success", {
            "reply": reply, "source": source, "session_id": session_id,
            "emotion": emotion,
            "gesture": _detect_gesture(reply, emotion),
        })
    finally:
        conn.close()

class SwitchModelRequest(BaseModel):
    model_key: str

@router.post("/api/digital-human/switch")
def switch_digital_human(req: SwitchModelRequest):
    """公开接口：切换数字人形象（演示用，无鉴权）"""
    if req.model_key not in MODEL_CATALOG:
        return Result(400, f"模型 '{req.model_key}' 不在可选目录中，可选：{', '.join(MODEL_CATALOG.keys())}")
    conn = get_db_connection()
    if not conn:
        return Result(503, "数据库不可用")
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE digital_human_configs SET is_active = FALSE")
            cursor.execute(
                "UPDATE digital_human_configs SET is_active = TRUE WHERE model_key = %s",
                (req.model_key,)
            )
            if cursor.rowcount == 0:
                cursor.execute(
                    """INSERT INTO digital_human_configs (model_key, name, voice_name, is_active)
                       VALUES (%s, %s, %s, TRUE)""",
                    (req.model_key, MODEL_CATALOG[req.model_key]["label"], MODEL_CATALOG[req.model_key]["default_voice"])
                )
        conn.commit()
        profile = get_active_profile()
        return Result(200, f"已切换到 {profile['name']}", profile)
    except Exception as exc:
        conn.rollback()
        return Result(500, f"切换失败：{exc}")
    finally:
        conn.close()

class DifyStatusResponse(BaseModel):
    api_key_configured: bool = False
    dataset_id_masked: str = ""
    reachable: bool = False

@router.get("/api/digital-human/dify-status")
def public_dify_status():
    """公开接口：返回本地向量知识库状态（替代 Dify 状态检查）。"""
    try:
        from app.services.vector_store import collection_exists, get_collection
        col = get_collection()
        return Result(200, "success", {
            "mode": "local_chromadb",
            "index_built": collection_exists(),
            "document_count": col.count() if col else 0,
            "reachable": collection_exists(),
        })
    except Exception:
        return Result(200, "success", {
            "mode": "local_chromadb",
            "index_built": False,
            "document_count": 0,
            "reachable": False,
        })

@router.get("/digital-human-3d", include_in_schema=False)
def digital_human_page():
    index_path = DIGITAL_HUMAN_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="digital human page not found")
    return FileResponse(index_path, headers={"Cache-Control": "no-store"})

# ── 地图数据 ──

SPOT_COORDS = {
    1:  (31.4248, 120.1038),  # 灵山大照壁（入口）
    2:  (31.4249, 120.1040),  # 五明桥
    3:  (31.4252, 120.1042),  # 佛足坛
    4:  (31.4255, 120.1044),  # 五智门
    5:  (31.4259, 120.1045),  # 菩提大道
    6:  (31.4263, 120.1045),  # 九龙灌浴
    7:  (31.4265, 120.1043),  # 降魔浮雕
    8:  (31.4268, 120.1040),  # 阿育王柱
    9:  (31.4270, 120.1046),  # 百子戏弥勒
    10: (31.4273, 120.1045),  # 祥符禅寺
    11: (31.4278, 120.1045),  # 灵山大佛
    12: (31.4274, 120.1050),  # 天下第一掌
    13: (31.4276, 120.1052),  # 佛教文化博览馆
    14: (31.4264, 120.1032),  # 灵山梵宫
    15: (31.4262, 120.1028),  # 五印坛城
    16: (31.4260, 120.1025),  # 曼飞龙塔
    17: (31.4266, 120.1035),  # 无尽意斋
    18: (31.4250, 120.1010),  # 拈花广场
    19: (31.4245, 120.1005),  # 梵天花海
    20: (31.4252, 120.1015),  # 香月花街
    21: (31.4255, 120.1020),  # 拈花堂
    22: (31.4248, 120.1020),  # 五灯湖
    23: (31.4240, 120.1015),  # 鹿鸣谷
}


ROUTE_PLANS = [
    {
        "id": 101,
        "name": "佛国中轴精华游",
        "duration": "2.5-3小时",
        "difficulty": "入门",
        "spot_orders": [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13],
    },
    {
        "id": 102,
        "name": "亲子互动祈福游",
        "duration": "4小时",
        "difficulty": "轻松",
        "spot_orders": [1, 2, 3, 6, 9, 10, 24, 25, 27, 26, 31, 32, 18],
    },
    {
        "id": 103,
        "name": "自然摄影慢游",
        "duration": "5小时",
        "difficulty": "普通",
        "spot_orders": [18, 20, 21, 22, 23, 19, 36],
    },
    {
        "id": 104,
        "name": "历史文化全景游",
        "duration": "6-7小时",
        "difficulty": "深度",
        "spot_orders": [1, 2, 3, 4, 5, 6, 9, 10, 24, 25, 27, 11, 13, 14, 15, 16],
    },
]

WAYPOINT_GRAPH = {
    1: [2],
    2: [1, 3],
    3: [2, 4],
    4: [3, 5],
    5: [4, 6],
    6: [5, 7, 9, 14, 29],
    7: [6, 8],
    8: [7, 10],
    9: [6, 10, 12],
    10: [8, 9, 11, 12],
    11: [10, 12, 13, 14],
    12: [9, 10, 11, 13],
    13: [11, 12],
    14: [6, 11, 15, 17, 18],
    15: [14, 16, 36],
    16: [15],
    17: [14],
    18: [14, 19, 20, 22],
    19: [18, 20, 23],
    20: [18, 19, 21, 22],
    21: [20, 22],
    22: [18, 20, 21, 23],
    23: [19, 22],
    24: [10, 25, 27],
    25: [24, 27, 26],
    26: [25, 27, 31],
    27: [10, 24, 25, 28],
    28: [14, 17, 27, 29, 30],
    29: [6, 28, 36],
    30: [14, 28],
    31: [26, 32],
    32: [18, 31],
    33: [34],
    34: [33, 35],
    35: [34, 36],
    36: [15, 29, 35],
    37: [24, 25, 38],
    38: [25, 26, 27, 37],
    39: [29, 40, 41],
    40: [39, 41, 42],
    41: [29, 39, 40],
    42: [40, 43],
    43: [42],
}


def _symmetrize_waypoint_graph(graph: dict[int, list[int]]) -> dict[int, list[int]]:
    undirected = {order: set(neighbors) for order, neighbors in graph.items()}
    for order, neighbors in graph.items():
        undirected.setdefault(order, set())
        for nxt in neighbors:
            undirected.setdefault(nxt, set()).add(order)
    return {order: sorted(neighbors) for order, neighbors in undirected.items()}


WAYPOINT_GRAPH = _symmetrize_waypoint_graph(WAYPOINT_GRAPH)

NAV_QUERY_PATTERN = re.compile(r"怎么走|往哪走|带我去|去.*怎么走|导航|从这到|到.*怎么走|去.*路线|我要去|我想去")


def _row_value(row, key: str, idx: int):
    return row[key] if isinstance(row, dict) else row[idx]


SUPPLEMENTAL_SPOTS = {
    24: {"name": "祥符寺旧迹", "category": "建筑", "description": "祥符禅寺周边历史遗迹节点。", "coord": (31.42845, 120.10095)},
    25: {"name": "白莲池", "category": "自然", "description": "祥符禅寺片区的水景节点。", "coord": (31.42810, 120.10185)},
    26: {"name": "杏坛广场", "category": "体验", "description": "灵山大佛片区的开阔广场。", "coord": (31.42785, 120.10095)},
    27: {"name": "大雄宝殿", "category": "建筑", "description": "祥符禅寺核心殿宇。", "coord": (31.42730, 120.10155)},
    28: {"name": "灵山泉", "category": "自然", "description": "灵山大佛与梵宫之间的休憩点。", "coord": (31.42655, 120.10210)},
    29: {"name": "养心亭", "category": "体验", "description": "游客休息与观景节点。", "coord": (31.42595, 120.10235)},
    30: {"name": "青年之家", "category": "体验", "description": "灵山梵宫北侧服务节点。", "coord": (31.42615, 120.10275)},
    31: {"name": "观光车吉坛广场上车换乘点", "category": "服务", "description": "景区观光车换乘点。", "coord": (31.42685, 120.10035)},
    32: {"name": "观光车佛手广场站", "category": "服务", "description": "佛手广场观光车站点。", "coord": (31.42555, 120.10115)},
    33: {"name": "灵山精舍凉亭", "category": "建筑", "description": "灵山精舍片区观景凉亭。", "coord": (31.42735, 120.10695)},
    34: {"name": "无锡佛教文化博览园", "category": "建筑", "description": "景区东侧文化展示片区。", "coord": (31.42645, 120.10715)},
    35: {"name": "群丰村", "category": "服务", "description": "景区东南侧地标。", "coord": (31.42575, 120.10695)},
    36: {"name": "祈福楼湖畔", "category": "自然", "description": "五印坛城外湖畔步道节点。", "coord": (31.42495, 120.10485)},
    37: {"name": "灵山胜境-灵山大佛", "category": "佛像", "description": "地图标注中的灵山大佛高位节点。", "coord": (31.42910, 120.10120)},
    38: {"name": "杏坛广场北区", "category": "体验", "description": "杏坛广场北侧步道节点。", "coord": (31.42795, 120.10180)},
    39: {"name": "慈恩宝塔", "category": "建筑", "description": "西南片区佛塔景点。", "coord": (31.42455, 120.10010)},
    40: {"name": "三圣殿", "category": "建筑", "description": "西南片区殿宇景点。", "coord": (31.42395, 120.10090)},
    41: {"name": "牡丹园", "category": "自然", "description": "西南片区园林景点。", "coord": (31.42395, 120.10175)},
    42: {"name": "净业堂", "category": "建筑", "description": "西南片区寺院节点。", "coord": (31.42305, 120.09995)},
    43: {"name": "崇德楼", "category": "建筑", "description": "西南片区楼阁节点。", "coord": (31.42375, 120.09935)},
}


def _load_map_spots(cursor) -> dict[int, dict]:
    cursor.execute("""
        SELECT id, name, category, description, sort_order
        FROM spots WHERE is_active = 1 ORDER BY sort_order
    """)
    spots: dict[int, dict] = {}
    for row in cursor.fetchall():
        order = int(_row_value(row, "sort_order", 4) or 0)
        coord = SPOT_COORDS.get(order)
        if not coord:
            continue
        lat, lng = _scale_point(coord[0], coord[1])
        spots[order] = {
            "id": _row_value(row, "id", 0),
            "name": _row_value(row, "name", 1),
            "category": _row_value(row, "category", 2),
            "description": _row_value(row, "description", 3) or "",
            "sort_order": order,
            "lat": lat,
            "lng": lng,
        }
    for order, extra in SUPPLEMENTAL_SPOTS.items():
        lat, lng = _scale_point(extra["coord"][0], extra["coord"][1])
        spots[order] = {
            "id": 100000 + order,
            "name": extra["name"],
            "category": extra["category"],
            "description": extra["description"],
            "sort_order": order,
            "lat": lat,
            "lng": lng,
        }
    return spots


def _find_target_spot(spots_by_order: dict[int, dict], question: str) -> dict | None:
    ordered = sorted(spots_by_order.values(), key=lambda spot: spot["sort_order"])
    for spot in ordered:
        if spot["name"] in question:
            return spot
    alias_map = {
        "大佛": "灵山大佛",
        "梵宫": "灵山梵宫",
        "坛城": "五印坛城",
        "禅寺": "祥符禅寺",
        "九龙": "九龙灌浴",
        "照壁": "灵山大照壁",
        "第一掌": "天下第一掌",
        "拈花湾": "拈花广场",
    }
    for alias, name in alias_map.items():
        if alias in question:
            for spot in ordered:
                if spot["name"] == name:
                    return spot
    return None


def _find_nearest_spot(spots_by_order: dict[int, dict], lat: float, lng: float) -> dict | None:
    best = None
    best_distance = float("inf")
    for spot in spots_by_order.values():
        distance = _haversine(lat, lng, spot["lat"], spot["lng"])
        if distance < best_distance:
            best_distance = distance
            best = spot | {"distance_m": round(distance)}
    return best


def _nearest_orders(spots_by_order: dict[int, dict], lat: float, lng: float, limit: int = 3) -> list[int]:
    ranked = []
    for order, spot in spots_by_order.items():
        ranked.append((_haversine(lat, lng, spot["lat"], spot["lng"]), order))
    ranked.sort(key=lambda item: item[0])
    return [order for _, order in ranked[:limit]]


def _path_distance_for_orders(spots_by_order: dict[int, dict], orders: list[int]) -> float:
    if len(orders) < 2:
        return 0.0
    total = 0.0
    for i in range(len(orders) - 1):
        a = spots_by_order.get(orders[i])
        b = spots_by_order.get(orders[i + 1])
        if not a or not b:
            continue
        total += _haversine(a["lat"], a["lng"], b["lat"], b["lng"])
    return total


def _shortest_waypoint_path(
    spots_by_order: dict[int, dict],
    start_orders: list[int],
    dest_order: int,
    start_lat: float | None = None,
    start_lng: float | None = None,
) -> list[int]:
    heap = []
    dist = {}
    prev = {}
    for order in start_orders:
        spot = spots_by_order.get(order)
        if not spot:
            continue
        base_cost = 0.0
        if start_lat is not None and start_lng is not None:
            base_cost = _haversine(start_lat, start_lng, spot["lat"], spot["lng"])
        dist[order] = base_cost
        heapq.heappush(heap, (base_cost, order))

    while heap:
        current_dist, order = heapq.heappop(heap)
        if order == dest_order:
            break
        if current_dist > dist.get(order, float("inf")):
            continue
        for nxt in WAYPOINT_GRAPH.get(order, []):
            a = spots_by_order.get(order)
            b = spots_by_order.get(nxt)
            if not a or not b:
                continue
            edge = _haversine(a["lat"], a["lng"], b["lat"], b["lng"])
            cand = current_dist + edge
            if cand < dist.get(nxt, float("inf")):
                dist[nxt] = cand
                prev[nxt] = order
                heapq.heappush(heap, (cand, nxt))

    if dest_order not in dist:
        return []

    path = [dest_order]
    cur = dest_order
    while cur in prev:
        cur = prev[cur]
        path.append(cur)
    path.reverse()
    return path


def _route_cost_between_orders(
    spots_by_order: dict[int, dict],
    start_order: int,
    dest_order: int,
) -> float:
    if start_order == dest_order:
        return 0.0
    path = _shortest_waypoint_path(spots_by_order, [start_order], dest_order)
    if not path:
        return float("inf")
    return _path_distance_for_orders(spots_by_order, path)


def _build_direct_navigation(spots_by_order: dict[int, dict], raw_lat: float, raw_lng: float, target_spot: dict) -> dict | None:
    # 当前位置是真实GPS/模拟坐标，不缩放；景点坐标才缩放
    current_lat, current_lng = raw_lat, raw_lng
    target_order = target_spot["sort_order"]
    start_orders = _nearest_orders(spots_by_order, current_lat, current_lng)
    waypoint_orders = _shortest_waypoint_path(
        spots_by_order,
        start_orders,
        target_order,
        start_lat=current_lat,
        start_lng=current_lng,
    )
    if not waypoint_orders:
        return None

    current_spot = _find_nearest_spot(spots_by_order, current_lat, current_lng)
    waypoints = [{
        "id": 0,
        "name": "当前位置",
        "lat": current_lat,
        "lng": current_lng,
    }]
    for order in waypoint_orders:
        spot = spots_by_order[order]
        waypoints.append({
            "id": spot["id"],
            "name": spot["name"],
            "lat": spot["lat"],
            "lng": spot["lng"],
        })

    anchors = [(w["lat"], w["lng"]) for w in waypoints]
    smooth = _build_smooth_path(anchors)
    geo_coords = [[lng, lat] for lat, lng in smooth]

    steps = []
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        a = waypoints[i]
        b = waypoints[i + 1]
        seg = _segment_path(anchors, i)
        seg_distance = _path_length(seg)
        total_distance += seg_distance
        bearing = _bearing(a["lat"], a["lng"], b["lat"], b["lng"])
        steps.append({
            "index": i,
            "from_id": a["id"],
            "from_name": a["name"],
            "to_id": b["id"],
            "to_name": b["name"],
            "from": [a["lng"], a["lat"]],
            "to": [b["lng"], b["lat"]],
            "distance_m": round(seg_distance),
            "duration_min": max(1, round(seg_distance / 70)),
            "direction": _direction_label(bearing),
            "instruction": _step_instruction(i, len(waypoints) - 1, a["name"], b["name"], bearing, seg_distance),
        })

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": geo_coords},
        "properties": {
            "id": 900000 + int(target_spot["id"]),
            "name": f"前往{target_spot['name']}",
            "duration": f"{max(1, round(total_distance / 70))}分钟",
            "difficulty": "实时导航",
            "color": "#0ea5e9",
            "total_distance_m": round(total_distance),
            "walking_min": max(1, round(total_distance / 70)),
            "stops": len(waypoints),
            "start_name": current_spot["name"] if current_spot else "当前位置",
            "end_name": target_spot["name"],
            "waypoints": waypoints,
            "steps": steps,
            "target_spot_id": target_spot["id"],
            "target_spot_name": target_spot["name"],
        },
    }


def _build_navigation_from_orders(
    spots_by_order: dict[int, dict],
    start_order: int,
    dest_order: int,
    start_name: str,
    start_id: int,
    color: str = "#0ea5e9",
    route_name: str | None = None,
) -> dict | None:
    if start_order == dest_order:
        return None
    waypoint_orders = _shortest_waypoint_path(spots_by_order, [start_order], dest_order)
    if not waypoint_orders:
        return None

    start_spot = spots_by_order.get(start_order)
    dest_spot = spots_by_order.get(dest_order)
    if not start_spot or not dest_spot:
        return None

    waypoints = [{
        "id": start_id,
        "name": start_name,
        "lat": start_spot["lat"],
        "lng": start_spot["lng"],
    }]
    for idx, order in enumerate(waypoint_orders):
        if idx == 0:
            continue
        spot = spots_by_order[order]
        waypoints.append({
            "id": spot["id"],
            "name": spot["name"],
            "lat": spot["lat"],
            "lng": spot["lng"],
        })

    anchors = [(w["lat"], w["lng"]) for w in waypoints]
    smooth = _build_smooth_path(anchors)
    geo_coords = [[lng, lat] for lat, lng in smooth]

    steps = []
    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        a = waypoints[i]
        b = waypoints[i + 1]
        seg = _segment_path(anchors, i)
        seg_distance = _path_length(seg)
        total_distance += seg_distance
        bearing = _bearing(a["lat"], a["lng"], b["lat"], b["lng"])
        steps.append({
            "index": i,
            "from_id": a["id"],
            "from_name": a["name"],
            "to_id": b["id"],
            "to_name": b["name"],
            "from": [a["lng"], a["lat"]],
            "to": [b["lng"], b["lat"]],
            "distance_m": round(seg_distance),
            "duration_min": max(1, round(seg_distance / 70)),
            "direction": _direction_label(bearing),
            "instruction": _step_instruction(i, len(waypoints) - 1, a["name"], b["name"], bearing, seg_distance),
        })

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": geo_coords},
        "properties": {
            "id": 910000 + int(dest_spot["id"]),
            "name": route_name or f"前往{dest_spot['name']}",
            "duration": f"{max(1, round(total_distance / 70))}分钟",
            "difficulty": "实时导航",
            "color": color,
            "total_distance_m": round(total_distance),
            "walking_min": max(1, round(total_distance / 70)),
            "stops": len(waypoints),
            "start_name": start_name,
            "end_name": dest_spot["name"],
            "waypoints": waypoints,
            "steps": steps,
            "target_spot_id": dest_spot["id"],
            "target_spot_name": dest_spot["name"],
        },
    }


def _build_plan_route_feature(
    spots_by_order: dict[int, dict],
    plan: dict,
    raw_lat: float,
    raw_lng: float,
    color: str = "#f76b1c",
) -> dict | None:
    start_lat, start_lng = raw_lat, raw_lng  # 当前位置不缩放，保持与前端模拟点位一致
    all_waypoints = [{
        "id": 0,
        "name": "当前位置",
        "lat": start_lat,
        "lng": start_lng,
    }]
    total_distance = 0.0
    steps = []
    last_order = None
    last_name = "当前位置"
    last_id = 0
    step_index = 0
    visited_orders: set[int] = set()

    optimized_orders = _optimize_plan_orders(spots_by_order, raw_lat, raw_lng, plan.get("spot_orders", []))
    for order in optimized_orders:
        spot = spots_by_order.get(order)
        if not spot:
            continue
        if last_order is None:
            partial = _build_direct_navigation(spots_by_order, raw_lat, raw_lng, spot)
        else:
            partial = _build_navigation_from_orders(
                spots_by_order,
                last_order,
                order,
                start_name=last_name,
                start_id=last_id,
                color=color,
                route_name=plan["name"],
            )
        if not partial:
            continue
        segment_waypoints = partial["properties"].get("waypoints", [])[1:]
        segment_steps = partial["properties"].get("steps", [])
        if not segment_waypoints or not segment_steps:
            continue
        for waypoint in segment_waypoints:
            current_order = int(waypoint["id"]) - 100000 if int(waypoint["id"]) >= 100000 else next(
                (spot_order for spot_order, spot_info in spots_by_order.items() if int(spot_info["id"]) == int(waypoint["id"])),
                None,
            )
            is_target_waypoint = current_order == order
            if all_waypoints and waypoint["name"] == all_waypoints[-1]["name"]:
                continue
            if current_order in visited_orders and not is_target_waypoint:
                continue
            all_waypoints.append(waypoint)
            if current_order is not None:
                visited_orders.add(current_order)
        for seg_step in segment_steps:
            if steps and seg_step["from_name"] == steps[-1]["to_name"] and seg_step["to_name"] == steps[-1]["from_name"]:
                continue
            seg_step = dict(seg_step)
            seg_step["index"] = step_index
            steps.append(seg_step)
            total_distance += seg_step["distance_m"]
            step_index += 1
        last_order = order
        last_name = spot["name"]
        last_id = spot["id"]

    if len(all_waypoints) < 2:
        return None

    anchors = [(w["lat"], w["lng"]) for w in all_waypoints]
    smooth = _build_smooth_path(anchors)
    geo_coords = [[lng, lat] for lat, lng in smooth]

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": geo_coords},
        "properties": {
            "id": 800000 + int(plan["id"]),
            "name": plan["name"],
            "duration": plan["duration"],
            "difficulty": plan["difficulty"],
            "color": color,
            "total_distance_m": round(total_distance),
            "walking_min": max(1, round(total_distance / 70)),
            "stops": len(all_waypoints),
            "start_name": "当前位置",
            "end_name": last_name,
            "waypoints": all_waypoints,
            "steps": steps,
            "plan_id": plan["id"],
            "plan_mode": "assembled_recommendation",
        },
    }


def _plan_matches_interest(plan: dict, interest: str | None) -> bool:
    if not interest:
        return True
    keywords = INTEREST_TO_PLAN_KEYWORDS.get(plan.get("difficulty", ""), [])
    return any(word in interest for word in keywords) or interest in plan.get("name", "")


def _optimize_plan_orders(
    spots_by_order: dict[int, dict],
    raw_lat: float,
    raw_lng: float,
    candidate_orders: list[int],
) -> list[int]:
    """按真实路网代价组装推荐顺序，尽量减少绕路和折返。"""
    remaining = [order for order in candidate_orders if order in spots_by_order]
    if not remaining:
        return []

    current_lat, current_lng = _scale_point(raw_lat, raw_lng)
    start_order = min(
        remaining,
        key=lambda order: _haversine(current_lat, current_lng, spots_by_order[order]["lat"], spots_by_order[order]["lng"]),
    )
    optimized = [start_order]
    remaining.remove(start_order)
    current_order = start_order

    while remaining:
        reachable = [
            (
                _route_cost_between_orders(spots_by_order, current_order, order),
                _haversine(current_lat, current_lng, spots_by_order[order]["lat"], spots_by_order[order]["lng"]),
                order,
            )
            for order in remaining
        ]
        reachable = [item for item in reachable if math.isfinite(item[0])]
        if not reachable:
            break
        reachable.sort(key=lambda item: (item[0], item[1]))
        _, _, best_order = reachable[0]
        optimized.append(best_order)
        current_lat = spots_by_order[best_order]["lat"]
        current_lng = spots_by_order[best_order]["lng"]
        current_order = best_order
        remaining.remove(best_order)
    return optimized


def _build_navigation_reply(question: str, location: dict | None, active_route_id: str | None, cursor) -> dict | None:
    if not NAV_QUERY_PATTERN.search(question):
        return None

    spots_by_order = _load_map_spots(cursor)
    if not spots_by_order:
        return None

    target_spot = _find_target_spot(spots_by_order, question)
    if not target_spot:
        return None

    if not location:
        return {
            "reply": f"好的，这就带你去{target_spot['name']}。我先帮你打开地图导航页，你到地图里定位后，我会继续按当前位置给你分段指路。",
            "emotion": "relaxed",
            "gesture": "point",
            "source": "navigation_intent",
            "target_spot_id": target_spot["id"],
            "target_spot_name": target_spot["name"],
            "route_action": {
                "type": "open_map_navigation",
                "target_spot_id": target_spot["id"],
                "target_spot_name": target_spot["name"],
            },
        }

    try:
        raw_lat = float(location.get("latitude"))
        raw_lng = float(location.get("longitude"))
    except (TypeError, ValueError):
        return {
            "reply": f"好的，这就带你去{target_spot['name']}。我先帮你打开地图导航页，你完成定位后，我会继续按当前位置给你分段指路。",
            "emotion": "relaxed",
            "gesture": "point",
            "source": "navigation_intent",
            "target_spot_id": target_spot["id"],
            "target_spot_name": target_spot["name"],
            "route_action": {
                "type": "open_map_navigation",
                "target_spot_id": target_spot["id"],
                "target_spot_name": target_spot["name"],
            },
        }

    route = _build_direct_navigation(spots_by_order, raw_lat, raw_lng, target_spot)
    if not route:
        return None

    props = route["properties"]
    steps = props.get("steps", [])
    if not steps:
        return None

    first_step = steps[0]
    second_step = steps[1] if len(steps) > 1 else None
    current_spot = _find_nearest_spot(
        spots_by_order,
        route["properties"]["waypoints"][0]["lat"],
        route["properties"]["waypoints"][0]["lng"],
    )

    route_hint = ""
    if active_route_id:
        for plan in ROUTE_PLANS:
            if str(plan["id"]) == str(active_route_id):
                route_hint = f" 你现在查看的是【{plan['name']}】。"
                break

    next_hint = (
        f" 到了{first_step['to_name']}之后，再前往{second_step['to_name']}。"
        if second_step
        else f" 继续按路线前往{first_step['to_name']}即可到达。"
    )
    reply = (
        f"你现在靠近{current_spot['name']}，如果要去{target_spot['name']}，"
        f"先{first_step['direction']}步行约{first_step['distance_m']}米，前往{first_step['to_name']}。"
        f"{next_hint} 全程大约{props['total_distance_m']}米，步行约{props['walking_min']}分钟。"
        f"{route_hint}如果你继续移动，我也可以按你当前的位置实时重算下一段路线。"
    )
    return {
        "reply": reply,
        "emotion": "relaxed",
        "gesture": "point",
        "source": "navigation_live",
        "target_spot_id": target_spot["id"],
        "target_spot_name": target_spot["name"],
        "route_action": {
            "type": "open_map_navigation",
            "target_spot_id": target_spot["id"],
            "target_spot_name": target_spot["name"],
        },
    }


@router.get("/api/map/spots")
def map_spots():
    """返回景点 GeoJSON"""
    conn = get_db_connection()
    features = []
    if conn:
        try:
            cursor = conn.cursor()
            for spot in _load_map_spots(cursor).values():
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [spot["lng"], spot["lat"]]},
                    "properties": {
                        "id": spot["id"],
                        "name": spot["name"],
                        "category": spot["category"],
                        "description": spot["description"][:120],
                    },
                })
            conn.close()
        except Exception:
            pass
    return {"type": "FeatureCollection", "features": features}


@router.get("/api/map/routes")
def map_routes():
    """返回路线 GeoJSON（含坐标串）

    优化内容：
    - 使用 Catmull-Rom 样条插值生成平滑曲线，避免硬折线
    - 每段路径插入垂直偏移的中间点，模拟真实步行小径的蜿蜒
    - 通过 SCALE 适度拉伸景点坐标间距，让路线在地图上视觉更舒展
    - 使用 Haversine 公式精确计算分段距离与步行用时
    - 返回百度地图样式的逐段导航步骤（properties.steps）
    """
    conn = get_db_connection()
    features = []
    colors = ["#3385ff", "#f76b1c", "#10b563", "#9b59b6"]
    if conn:
        try:
            cursor = conn.cursor()
            spots_by_order = _load_map_spots(cursor)
            for idx, plan in enumerate(ROUTE_PLANS):
                rid = plan["id"]
                name = plan["name"]
                dur = plan["duration"]
                diff = plan["difficulty"]

                # —— 收集途经景点。按 sort_order 取坐标，不依赖数据库自增 id ——
                waypoints = []
                for order in plan["spot_orders"]:
                    spot = spots_by_order.get(order)
                    if spot:
                        waypoints.append((spot["id"], spot["lat"], spot["lng"], spot["name"]))

                if len(waypoints) < 2:
                    continue

                # —— 生成平滑路径坐标 ——
                anchors = [(w[1], w[2]) for w in waypoints]
                smooth = _build_smooth_path(anchors)
                # GeoJSON 经度在前
                geo_coords = [[lng, lat] for lat, lng in smooth]

                # —— 分段距离与导航步骤（百度地图样式） ——
                steps = []
                total_distance = 0.0
                for i in range(len(waypoints) - 1):
                    a = waypoints[i]
                    b = waypoints[i + 1]
                    seg = _segment_path(anchors, i)
                    seg_distance = _path_length(seg)
                    total_distance += seg_distance
                    bearing = _bearing(a[1], a[2], b[1], b[2])
                    steps.append({
                        "index": i,
                        "from_id": a[0],
                        "from_name": a[3],
                        "to_id": b[0],
                        "to_name": b[3],
                        "from": [a[2], a[1]],
                        "to": [b[2], b[1]],
                        "distance_m": round(seg_distance),
                        "duration_min": max(1, round(seg_distance / 70)),  # 步行约 70 m/min
                        "direction": _direction_label(bearing),
                        "instruction": _step_instruction(i, len(waypoints) - 1, a[3], b[3], bearing, seg_distance),
                    })

                total_min = max(1, round(total_distance / 70))
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": geo_coords},
                    "properties": {
                        "id": rid,
                        "name": name,
                        "duration": dur,
                        "difficulty": diff,
                        "color": colors[idx % len(colors)],
                        "total_distance_m": round(total_distance),
                        "walking_min": total_min,
                        "stops": len(waypoints),
                        "start_name": waypoints[0][3],
                        "end_name": waypoints[-1][3],
                        "waypoints": [
                            {"id": w[0], "name": w[3], "lat": w[1], "lng": w[2]} for w in waypoints
                        ],
                        "steps": steps,
                    },
                })
            conn.close()
        except Exception:
            pass
    return {"type": "FeatureCollection", "features": features}


@router.post("/api/map/route/live")
def map_live_route(req: MapLiveRouteRequest):
    """根据当前位置/测试点实时生成到目标景点的分段导航路线。"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="地图服务暂不可用")

    try:
        cursor = conn.cursor()
        spots_by_order = _load_map_spots(cursor)
        if not spots_by_order:
            raise HTTPException(status_code=404, detail="未找到景点数据")

        target_spot = None
        if req.target_spot_id is not None:
            for spot in spots_by_order.values():
                if int(spot["id"]) == int(req.target_spot_id):
                    target_spot = spot
                    break
        if not target_spot and req.target_name:
            target_spot = _find_target_spot(spots_by_order, req.target_name)
        if not target_spot:
            raise HTTPException(status_code=404, detail="未找到目标景点")

        feature = _build_direct_navigation(spots_by_order, req.latitude, req.longitude, target_spot)
        if not feature:
            raise HTTPException(status_code=404, detail="未找到可用路线")
        return feature
    finally:
        conn.close()


@router.get("/api/map/recommendations")
def map_recommendations(latitude: float, longitude: float, interest: str | None = None):
    """基于当前位置组装推荐路线，复用项目既有路线推荐思路。"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="地图服务暂不可用")

    try:
        cursor = conn.cursor()
        spots_by_order = _load_map_spots(cursor)
        features = []
        colors = ["#f76b1c", "#10b563", "#8b5cf6", "#ef4444"]
        plans = [plan for plan in ROUTE_PLANS if _plan_matches_interest(plan, interest)]
        if not plans:
            plans = ROUTE_PLANS
        for idx, plan in enumerate(plans):
            feature = _build_plan_route_feature(
                spots_by_order,
                plan,
                latitude,
                longitude,
                color=colors[idx % len(colors)],
            )
            if feature:
                features.append(feature)
        return {"type": "FeatureCollection", "features": features}
    finally:
        conn.close()


# ── 路径平滑 / 几何工具 ──

# 将原坐标围绕中心做轻度放大，让导航路线在地图上的距离感更明显
_SCALE_CENTER = (31.4258, 120.1030)
_SCALE_FACTOR = 1.45


def _scale_point(lat: float, lng: float) -> tuple[float, float]:
    return (
        _SCALE_CENTER[0] + (lat - _SCALE_CENTER[0]) * _SCALE_FACTOR,
        _SCALE_CENTER[1] + (lng - _SCALE_CENTER[1]) * _SCALE_FACTOR,
    )


def _fetch_spot_names(cursor, sid_list: list[int]) -> dict[int, str]:
    if not sid_list:
        return {}
    try:
        placeholders = ",".join(["%s"] * len(sid_list))
        cursor.execute(f"SELECT id, name FROM spots WHERE id IN ({placeholders})", tuple(sid_list))
        out: dict[int, str] = {}
        for r in cursor.fetchall():
            sid = r["id"] if isinstance(r, dict) else r[0]
            nm = r["name"] if isinstance(r, dict) else r[1]
            out[sid] = nm
        return out
    except Exception:
        return {}


def _segment_midpoints(a: tuple[float, float], b: tuple[float, float], offset_sign: int) -> list[tuple[float, float]]:
    """在 a→b 之间生成两个垂直偏移的中间锚点，让路径呈缓和的 S 形。"""
    lat1, lng1 = a
    lat2, lng2 = b
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    # 垂直方向（在赤道附近近似），并按经纬度比例修正
    perp_lat = -dlng * math.cos(math.radians((lat1 + lat2) / 2))
    perp_lng = dlat / max(math.cos(math.radians((lat1 + lat2) / 2)), 1e-6)
    norm = math.hypot(perp_lat, perp_lng) or 1.0
    base_len = math.hypot(dlat, dlng)
    # 偏移幅度随段长成比例，约段长的 12%
    amp = base_len * 0.12 * offset_sign
    perp_lat = perp_lat / norm * amp
    perp_lng = perp_lng / norm * amp
    m1 = (lat1 + dlat * 0.33 + perp_lat, lng1 + dlng * 0.33 + perp_lng)
    m2 = (lat1 + dlat * 0.66 + perp_lat * 0.7, lng1 + dlng * 0.66 + perp_lng * 0.7)
    return [m1, m2]


def _expand_with_offsets(anchors: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """在每对锚点之间插入偏移中点，方向交替。"""
    expanded: list[tuple[float, float]] = [anchors[0]]
    for i in range(len(anchors) - 1):
        sign = 1 if i % 2 == 0 else -1
        expanded.extend(_segment_midpoints(anchors[i], anchors[i + 1], sign))
        expanded.append(anchors[i + 1])
    return expanded


def _catmull_rom(points: list[tuple[float, float]], samples: int = 14) -> list[tuple[float, float]]:
    """Catmull-Rom 样条平滑：返回平滑后的坐标序列。"""
    if len(points) < 2:
        return list(points)
    pts = [points[0]] + list(points) + [points[-1]]
    out: list[tuple[float, float]] = []
    for i in range(len(pts) - 3):
        p0, p1, p2, p3 = pts[i], pts[i + 1], pts[i + 2], pts[i + 3]
        for s in range(samples):
            t = s / samples
            t2 = t * t
            t3 = t2 * t
            lat = 0.5 * (
                (2 * p1[0])
                + (-p0[0] + p2[0]) * t
                + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3
            )
            lng = 0.5 * (
                (2 * p1[1])
                + (-p0[1] + p2[1]) * t
                + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3
            )
            out.append((lat, lng))
    out.append(points[-1])
    return out


def _build_smooth_path(anchors: list[tuple[float, float]]) -> list[tuple[float, float]]:
    expanded = _expand_with_offsets(anchors)
    return _catmull_rom(expanded, samples=12)


def _segment_path(anchors: list[tuple[float, float]], i: int) -> list[tuple[float, float]]:
    """单段（第 i 个景点 → 第 i+1 个景点）的平滑坐标，用于分段距离计算。"""
    sign = 1 if i % 2 == 0 else -1
    pair = [anchors[i]] + _segment_midpoints(anchors[i], anchors[i + 1], sign) + [anchors[i + 1]]
    return _catmull_rom(pair, samples=10)


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _path_length(coords: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(coords) - 1):
        total += _haversine(coords[i][0], coords[i][1], coords[i + 1][0], coords[i + 1][1])
    return total


def _bearing(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lng2 - lng1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    deg = (math.degrees(math.atan2(x, y)) + 360) % 360
    return deg


_DIRECTIONS = [
    (22.5, "向北"), (67.5, "向东北"), (112.5, "向东"), (157.5, "向东南"),
    (202.5, "向南"), (247.5, "向西南"), (292.5, "向西"), (337.5, "向西北"),
]


def _direction_label(bearing: float) -> str:
    for lim, label in _DIRECTIONS:
        if bearing < lim:
            return label
    return "向北"


def _step_instruction(i: int, last_idx: int, from_name: str, to_name: str, bearing: float, distance: float) -> str:
    direction = _direction_label(bearing)
    dist_text = f"{round(distance)} 米" if distance < 1000 else f"{distance / 1000:.1f} 公里"
    if i == 0:
        return f"从 {from_name} 出发，{direction}步行 {dist_text}，前往 {to_name}"
    if i == last_idx - 1:
        return f"{direction}继续步行 {dist_text}，到达终点 {to_name}"
    return f"{direction}步行 {dist_text}，途经 {to_name}"


@router.get("/digital-human-3d/map", include_in_schema=False)
def map_page():
    map_path = DIGITAL_HUMAN_DIR / "map.html"
    if not map_path.exists():
        raise HTTPException(status_code=404, detail="map page not found")
    return FileResponse(map_path)


LIVE2D_DIST_DIR = BASE_DIR / "digital_human" / "live2d_host" / "live2d" / "dist"


@router.get("/Resources/{path:path}", include_in_schema=False)
def live2d_resources_fix(path: str):
    """
    Live2D SDK 内部使用 ../../Resources/ 相对路径加载模型文件。
    由于 iframe 页面位于 /live2d/index.html，浏览器会将 ../../Resources/
    解析为 /Resources/（回退到根目录）。
    此路由将 /Resources/* 映射到 dist/Resources/*。
    """
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        raise HTTPException(status_code=403, detail="forbidden")
    file_path = (LIVE2D_DIST_DIR / "Resources" / safe_path).resolve()
    if not str(file_path).startswith(str(LIVE2D_DIST_DIR.resolve())):
        raise HTTPException(status_code=403, detail="forbidden")
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"live2d resource not found: {path}")
    mt = _mime_type(str(file_path))
    return FileResponse(file_path, media_type=mt, headers={"Cache-Control": "no-store"})


LIVE2D_RESOURCES_DIR = LIVE2D_DIST_DIR / "Resources"


@router.get("/live2d/{path:path}", include_in_schema=False)
def live2d_static(path: str):
    """提供 Live2D 编译产物（dist/ 下的所有文件）"""
    safe_path = os.path.normpath(path)
    if safe_path.startswith("..") or os.path.isabs(safe_path):
        raise HTTPException(status_code=403, detail="forbidden")
    file_path = (LIVE2D_DIST_DIR / safe_path).resolve()
    if not str(file_path).startswith(str(LIVE2D_DIST_DIR.resolve())):
        raise HTTPException(status_code=403, detail="forbidden")
    if not file_path.exists() or not file_path.is_file():
        # 如果是目录或没有扩展名，尝试 index.html
        if file_path.is_dir():
            file_path = file_path / "index.html"
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="live2d asset not found")
        else:
            raise HTTPException(status_code=404, detail="live2d asset not found")
    mt = _mime_type(str(file_path))
    return FileResponse(file_path, media_type=mt, headers={"Cache-Control": "no-store"})


def _mime_type(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    return {
        ".html": "text/html", ".js": "application/javascript", ".json": "application/json",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".css": "text/css", ".moc3": "application/octet-stream",
        ".cdi3": "application/json", ".physics3": "application/json",
        ".pose3": "application/json", ".exp3": "application/json",
        ".motion3": "application/json", ".userdata3": "application/json",
    }.get(ext, "application/octet-stream")


@router.get("/digital-human-3d/leaflet/{filename}", include_in_schema=False)
def leaflet_assets(filename: str):
    """提供 Leaflet 静态文件"""
    allowed = {"leaflet.css", "leaflet.js"}
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="asset not found")
    file_path = DIGITAL_HUMAN_DIR / "leaflet" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="asset not found")
    mt = "text/css" if filename.endswith(".css") else "application/javascript"
    return FileResponse(file_path, media_type=mt)
