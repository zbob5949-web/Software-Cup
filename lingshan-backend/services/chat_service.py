#这段代码是智能对话系统的核心服务层，实现了景区数字人"灵小佑"的完整问答逻辑。它整合了多种知识来源和智能路由策略。
'''''六大知识来源（按优先级）
   优先级	来源	说明	场景示例
1️⃣	FAQ	 本地高频问答库精准匹配	"门票多少钱" → 标准答案
2️⃣	即时服务	厕所、餐饮、急救等应急需求	"想上厕所" → 引导到附近卫生间
3️⃣	路线推荐	基于时长/兴趣的个性化规划	"带老人玩3小时" → 推荐轻松路线
4️⃣	景点直答	景区数据库结构化信息	"灵山大佛多高" → 88米
5️⃣	Dify知识库	RAG检索增强生成	深度文化背景知识
6️⃣	DeepSeek AI	大模型综合生成	复杂开放性问题
生成一句话的是形式'''
import re
import requests
from datetime import datetime
from core.config import DEEPSEEK_KEY, DIFY_API_KEY, DIFY_DATASET_ID, DIFY_BASE_URL
from utils.faq_matcher import match_faq
import logging

logger = logging.getLogger(__name__)

# ============================================================
# 本地景点/路线知识库检索
# ============================================================

#景点别名映射
SPOT_ALIASES = {
    "灵山大佛": ["灵山大佛", "大佛", "佛脚", "抱佛脚", "登云道"],
    "灵山梵宫": ["灵山梵宫", "梵宫", "吉祥颂", "东方卢浮宫"],
    "九龙灌浴": ["九龙灌浴", "九龙", "灌浴", "圣水"],
    "五印坛城": ["五印坛城", "坛城", "转经筒", "小布达拉宫"],
    "祥符禅寺": ["祥符禅寺", "禅寺", "寺庙", "撞钟"],
    "百子戏弥勒": ["百子戏弥勒", "弥勒", "弥勒佛"],
    "天下第一掌": ["天下第一掌", "佛手", "第一掌", "摸掌"],
    "佛教文化博览馆": ["佛教文化博览馆", "博览馆", "万佛殿"],
    "灵山大照壁": ["灵山大照壁", "大照壁", "照壁"],
    "菩提大道": ["菩提大道", "菩提树"],
    "五明桥": ["五明桥"],
    "佛足坛": ["佛足坛", "佛足印", "佛足"],
    "五智门": ["五智门"],
    "曼飞龙塔": ["曼飞龙塔", "飞龙塔", "白塔"],
    "无尽意斋": ["无尽意斋", "赵朴初故居"],
    "拈花湾": ["拈花湾", "禅意小镇"],
    "拈花广场": ["拈花广场", "拈花微笑"],
    "梵天花海": ["梵天花海", "花海"],
    "香月花街": ["香月花街", "花街"],
    "拈花堂": ["拈花堂"],
    "五灯湖": ["五灯湖", "禅行", "灯光秀"],
    "鹿鸣谷": ["鹿鸣谷"],
}

#即时服务回答
SERVICE_ANSWERS = [
    (
        ("厕所", "卫生间", "洗手间"),
        "景区常用卫生间位置：灵山大佛广场、九龙灌浴广场、梵宫入口/出口、五印坛城周边、香月花街均有公共卫生间。您如果能告诉我当前位置，我可以按最近点帮您指引。",
    ),
    (
        ("吃饭", "餐厅", "饿", "素斋", "素面", "美食"),
        "用餐推荐：灵山主景区可去梵宫素斋自助（约50元/位）或景区素面套餐（约35元/位）；拈花湾可去香月花街，餐饮和禅茶选择更多。",
    ),
    (
        ("观光车", "坐车", "电瓶车", "景交"),
        "灵山胜境有观光车服务，单独购票约40元/人；若时间紧或带老人儿童，建议购买含观光车的联票，按景区站点乘坐更省体力。",
    ),
    (
        ("迷路", "找不到", "怎么走", "导航", "方向"),
        "别着急。灵山胜境主轴线大致为：入口大照壁 → 五明桥/佛足坛 → 五智门 → 九龙灌浴 → 祥符禅寺/灵山大佛 → 梵宫/五印坛城。请告诉我您现在看到的景点或标识，我再给您具体方向。",
    ),
    (
        ("丢", "遗失", "失物", "找不到东西"),
        "如果物品遗失，建议尽快联系景区游客服务中心或就近工作人员，并说明遗失时间、地点、物品特征；同时可沿刚才游览路线回看。",
    ),
    (
        ("受伤", "不舒服", "难受", "晕", "急救", "医务"),
        "如果身体不适或受伤，请先到阴凉安全处休息，并立即联系附近工作人员或游客服务中心；紧急情况请拨打120。景区工作人员可协助引导至医疗/急救点。",
    ),
]

def search_local_knowledge(cursor, query: str) -> str:
    """
    从 spots 和 routes 表中检索与用户问题相关的数据，
    作为 AI 回答的上下文补充
    """
    parts = []
    try:
        # 搜景点 — 同时匹配名称和描述
        terms = _extract_search_terms(query)
        like_clauses = " OR ".join(["name LIKE %s OR description LIKE %s"] * len(terms))
        params = []
        for term in terms:
            params.extend([f"%{term}%", f"%{term}%"])
        cursor.execute(
            "SELECT name, category, description, open_time, duration, tips "
            "FROM spots WHERE is_active = TRUE "
            f"AND ({like_clauses}) LIMIT 3",
            params
        )
        for row in cursor.fetchall():
            if isinstance(row, dict):
                parts.append(
                    f"【{row['name']}】(类别:{row['category']}) "
                    f"简介:{row['description'][:200]} "
                    f"开放:{row['open_time']} 建议:{row['duration']}"
                )
            else:
                parts.append(
                    f"【{row[0]}】(类别:{row[1]}) "
                    f"简介:{row[2][:200] if row[2] else ''} "
                    f"开放:{row[3]} 建议:{row[4]}"
                )
        # 搜路线
        route_clauses = " OR ".join(["name LIKE %s OR description LIKE %s OR difficulty LIKE %s"] * len(terms))
        route_params = []
        for term in terms:
            route_params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        cursor.execute(
            "SELECT name, duration, difficulty, description FROM routes "
            f"WHERE is_active = TRUE AND ({route_clauses}) LIMIT 2",
            route_params
        )
        for row in cursor.fetchall():
            if isinstance(row, dict):
                parts.append(
                    f"【路线:{row['name']}】({row['duration']}/{row['difficulty']}) "
                    f"{row['description'][:200]}"
                )
            else:
                parts.append(
                    f"【路线:{row[0]}】({row[1]}/{row[2]}) "
                    f"{row[3][:200] if row[3] else ''}"
                )
    except Exception as e:
        logger.warning(f"本地知识检索失败: {e}")

    return "\n".join(parts) if parts else ""


def _extract_search_terms(query: str) -> list[str]:
    """从自然语言问题中抽取适合 SQL LIKE 的短关键词。"""
    q = (query or "").strip()
    terms = []
    for spot_name, aliases in SPOT_ALIASES.items():
        if any(alias in q for alias in aliases):
            terms.append(spot_name)
            terms.extend([a for a in aliases if len(a) >= 2])
    for keyword in ["历史", "文化", "自然", "风光", "摄影", "亲子", "家庭", "儿童", "老人", "演出", "祈福", "禅意", "艺术", "门票", "开放时间"]:
        if keyword in q:
            terms.append(keyword)
    if q and len(q) <= 20:
        terms.append(q)
    # 去重并避免过长问题导致 LIKE 无效
    deduped = []
    for term in terms:
        if term and term not in deduped:
            deduped.append(term)
    return deduped or [q[:20] or "灵山"]


def answer_instant_service(query: str) -> str:
    """对厕所、餐饮、迷路等即时服务诉求给出稳定直答，避免误介绍景点。"""
    q = query or ""
    for keywords, answer in SERVICE_ANSWERS:
        if any(keyword in q for keyword in keywords):
            return answer
    return ""


def answer_route_recommendation(cursor, query: str) -> str:
    """根据兴趣/游览时长给出个性化路线推荐。"""
    q = query or ""
    route_intent_words = ("路线", "推荐", "规划", "怎么玩", "游览", "感兴趣", "喜欢", "适合")
    if not any(word in q for word in route_intent_words):
        return ""

    hours = None
    hour_match = re.search(r"(\d{1,2})\s*(?:个)?小时", q)
    if hour_match:
        hours = int(hour_match.group(1))

    difficulty = None
    interest_map = {
        "历史": "深度", "文化": "深度", "佛教": "深度", "艺术": "深度",
        "自然": "普通", "风光": "普通", "摄影": "普通", "太湖": "普通",
        "亲子": "轻松", "家庭": "轻松", "儿童": "轻松", "老人": "轻松",
        "入门": "入门", "时间少": "入门", "轻松": "轻松", "深度": "深度",
    }
    for keyword, value in interest_map.items():
        if keyword in q:
            difficulty = value
            break

    if difficulty:
        cursor.execute(
            "SELECT id, name, duration, difficulty, description, spot_ids "
            "FROM routes WHERE is_active = TRUE AND difficulty = %s "
            "ORDER BY hours_min ASC LIMIT 1",
            (difficulty,),
        )
    elif hours is not None:
        cursor.execute(
            "SELECT id, name, duration, difficulty, description, spot_ids "
            "FROM routes WHERE is_active = TRUE "
            "ORDER BY ABS((hours_min + hours_max) / 2 - %s) ASC LIMIT 1",
            (hours,),
        )
    else:
        return ""
    route = cursor.fetchone()
    if not route:
        return ""

    spot_names = []
    spot_ids = route.get("spot_ids") if isinstance(route, dict) else route[5]
    if spot_ids:
        ids = [int(i) for i in spot_ids.split(",") if i.strip().isdigit()]
        if ids:
            fmt = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"SELECT id, name FROM spots WHERE id IN ({fmt}) ORDER BY FIELD(id, {fmt})",
                ids + ids,
            )
            spot_names = [r["name"] for r in cursor.fetchall()]

    name = route["name"] if isinstance(route, dict) else route[1]
    duration = route["duration"] if isinstance(route, dict) else route[2]
    desc = route["description"] if isinstance(route, dict) else route[4]
    reply = f"为您推荐【{name}】（{duration}）。\n"
    if spot_names:
        reply += "路线顺序：" + " → ".join(spot_names) + "\n"
    reply += desc or ""
    return reply[:900]


def answer_from_spot_name(cursor, query: str) -> str:
    """当问题中提及具体景点时，给出固定统一的景点相关答复。"""
    cursor.execute(
        "SELECT name, category, description, open_time, duration, tips "
        "FROM spots WHERE is_active = TRUE ORDER BY CHAR_LENGTH(name) DESC"
    )
    rows = cursor.fetchall()
    normalized_query = query.strip()
    for row in rows:
        name = row["name"] if isinstance(row, dict) else row[0]
        aliases = SPOT_ALIASES.get(name, [name])
        matched = name and (name in normalized_query or normalized_query in name)
        matched = matched or any(alias and alias in normalized_query for alias in aliases)
        if matched:
            category = row["category"] if isinstance(row, dict) else row[1]
            description = row["description"] if isinstance(row, dict) else row[2]
            open_time = row["open_time"] if isinstance(row, dict) else row[3]
            duration = row["duration"] if isinstance(row, dict) else row[4]
            tips = row["tips"] if isinstance(row, dict) else row[5]
            reply = f"{name}是灵山胜境的{category or '景点'}。{description or ''}"
            if open_time:
                reply += f"\n\n开放时间：{open_time}"
            if duration:
                reply += f"\n建议游览：{duration}"
            if tips:
                reply += f"\n游览提示：{tips}"
            return reply[:900]
    return ""


# ============================================================
# DeepSeek 调用
# ============================================================

def call_deepseek(messages: list) -> str:
    if not DEEPSEEK_KEY:
        return "AI服务未配置，请联系管理员"
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.7,
            "stream": False
        }
        resp = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload, headers=headers, timeout=30
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"].strip()
        return "大模型暂时不可用，请稍后再试"
    except Exception:
        return "服务异常，请重试"


# ============================================================
# Dify 知识库检索
# ============================================================

def retrieve_from_dify(query: str) -> str:
    if not DIFY_API_KEY or not DIFY_DATASET_ID:
        return ""
    try:
        url = f"{DIFY_BASE_URL}/datasets/{DIFY_DATASET_ID}/retrieve"
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {"query": query, "retrieval_model": {"search_method": "hybrid_search", "top_k": 3}}
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        if resp.status_code == 200:
            records = resp.json().get("records", [])
            if records:
                contents = []
                for record in records[:3]:
                    # Dify 新版知识库检索返回 records[].segment.content；
                    # 旧版/部分网关可能返回 records[].content，这里同时兼容。
                    content = (
                        (record.get("segment") or {}).get("content")
                        or record.get("content")
                        or record.get("summary")
                        or ""
                    )
                    if content:
                        contents.append(content)
                return "\n\n".join(contents)
        return ""
    except Exception:
        return ""


# ============================================================
# 数字人表情/动作/口型同步提示
# ============================================================

def infer_digital_human_directives(question: str, reply: str, source: str = None) -> dict:
    """根据问答内容给前端数字人返回轻量驱动提示。

    后端不直接生成真实 viseme 时间轴，真实口型同步通常由前端数字人 SDK
    基于音频实时分析；这里提供情绪、表情、动作、口型同步策略等结构化字段，
    让管理后台/游客端展示时能体现“表情和口型同步”的后端支持。
    """
    text = f"{question or ''}\n{reply or ''}"
    if any(word in text for word in ["受伤", "不舒服", "急救", "投诉", "不满", "差", "迷路", "丢"]):
        emotion = "concerned"
        expression = "关切"
        actions = ["安抚", "指引"]
        speaking_style = "放慢语速，语气安抚"
    elif any(word in text for word in ["祈福", "拜佛", "许愿", "禅", "佛", "文化", "历史"]):
        emotion = "peaceful"
        expression = "温和"
        actions = ["合十", "讲解"]
        speaking_style = "平和、庄重"
    elif any(word in text for word in ["推荐", "路线", "怎么玩", "适合", "游览"]):
        emotion = "guide"
        expression = "热情"
        actions = ["指路", "展示路线"]
        speaking_style = "清晰、有引导感"
    elif any(word in text for word in ["谢谢", "喜欢", "开心", "满意", "不错", "漂亮", "震撼"]):
        emotion = "happy"
        expression = "微笑"
        actions = ["点头", "欢迎"]
        speaking_style = "轻快、亲切"
    else:
        emotion = "neutral"
        expression = "自然微笑"
        actions = ["讲解"]
        speaking_style = "亲切、自然"

    return {
        "emotion": emotion,
        "expression": expression,
        "action_keywords": actions,
        "speaking_style": speaking_style,
        "mouth_sync": {
            "mode": "audio_driven",
            "hint": "前端数字人可根据返回音频做口型同步；无音频时可按文本长度估算说话时长。",
        },
        "source": source or "unknown",
    }


# ============================================================
# 构造 messages
# ============================================================

def build_messages(question: str, history: list = None, dify_context: str = None,
                   local_context: str = None) -> list:
    """
    构造 DeepSeek messages，整合多种知识来源
    """
    system_prompt = """你是灵山景区智能助手"灵小佑"。

灵山胜境景区包含以下区域：
- 灵山胜境主景区：灵山大佛、九龙灌浴、灵山梵宫、五印坛城、祥符禅寺、菩提大道等
- 拈花湾禅意小镇：拈花广场、梵天花海、香月花街、拈花堂、五灯湖、鹿鸣谷等
- 景区内设有餐厅（梵宫素斋50元/位、素面35元/位）、观光车服务（40元/人）、导游讲解（300元起）

【回答前必须先判断游客的真实需求，按以下优先级处理】：

第一优先：游客有即时服务需求
→ 找厕所/卫生间 → 告知附近卫生间位置，大佛广场、梵宫入口、九龙灌浴广场均设有公共卫生间
→ 找餐厅/饿了 → 推荐梵宫素斋或香月花街
→ 身体不适/受伤 → 告知景区急救站位置，建议联系景区工作人员
→ 东西丢了 → 告知景区失物招领处
→ 迷路/找不到地方 → 根据游客当前位置给出方向指引
→ 要买水/买东西 → 告知附近商铺位置

第二优先：游客提到地名只是说明位置
→ "我在灵山大佛想上厕所" → 解决厕所需求，不介绍大佛
→ "在梵宫附近哪里吃饭" → 推荐附近餐厅

第三优先：游客明确询问景点信息、路线、门票、演出
→ 详细准确地回答景区相关问题，优先使用下方提供的景区数据

回答热情、准确、简洁，不超过200字。遇到不确定的情况先问清楚游客需要什么。"""

    # 拼接知识来源
    if local_context:
        system_prompt += f"\n\n【景区数据库参考】：\n{local_context}"
    if dify_context:
        system_prompt += f"\n\n【知识库补充参考】：\n{dify_context}"

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


# ============================================================
# 消息持久化
# ============================================================

def save_message(cursor, session_id: str, phone: str, role: str, content: str, source: str = None):
    cursor.execute(
        "INSERT INTO chat_records (session_id, phone, role, content, source, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (session_id, phone, role, content, source, datetime.now())
    )


def cleanup_old_records(cursor, session_id: str, phone: str = None, max_records: int = 20):
    if phone:
        cursor.execute(
            "SELECT id FROM chat_records WHERE session_id = %s AND phone = %s "
            "ORDER BY id DESC LIMIT 1 OFFSET %s",
            (session_id, phone, max_records)
        )
    else:
        cursor.execute(
            "SELECT id FROM chat_records WHERE session_id = %s AND phone IS NULL "
            "ORDER BY id DESC LIMIT 1 OFFSET %s",
            (session_id, max_records)
        )
    old = cursor.fetchone()
    if old:
        old_id = old["id"] if isinstance(old, dict) else old[0]
        if phone:
            cursor.execute(
                "DELETE FROM chat_records WHERE session_id = %s AND phone = %s AND id < %s",
                (session_id, phone, old_id)
            )
        else:
            cursor.execute(
                "DELETE FROM chat_records WHERE session_id = %s AND phone IS NULL AND id < %s",
                (session_id, old_id)
            )


# ============================================================
# 核心对话处理
# ============================================================

def process_user_chat(cursor, user_question: str, session_id: str,
                      phone: str = None) -> dict:
    # 1. FAQ 精准匹配
    faq_matches = match_faq(cursor, user_question)
    if faq_matches:
        best = faq_matches[0]
        return {"reply": best["answer"], "source": "faq"}

    # 2. 即时服务诉求直答（厕所、餐饮、迷路等），避免把位置词误判成景点讲解
    service_answer = answer_instant_service(user_question)
    if service_answer:
        return {"reply": service_answer, "source": "service"}

    # 3. 个性化路线推荐直答，满足“按兴趣推荐路线和讲解重点”的核心需求
    route_answer = answer_route_recommendation(cursor, user_question)
    if route_answer:
        return {"reply": route_answer, "source": "route"}

    # 4. 本地景点名直答，保证核心事实问答不依赖外部大模型
    spot_answer = answer_from_spot_name(cursor, user_question)
    if spot_answer:
        return {"reply": spot_answer, "source": "spot"}

    # 5. 本地知识库检索（spots/routes表）
    local_context = search_local_knowledge(cursor, user_question)

    # 6. Dify 知识库检索
    dify_context = retrieve_from_dify(user_question) if DIFY_API_KEY and DIFY_DATASET_ID else ""

    # 5. 获取会话历史（最近6轮）
    if phone:
        cursor.execute(
            "SELECT role, content FROM chat_records "
            "WHERE session_id = %s AND phone = %s ORDER BY id DESC LIMIT 12",
            (session_id, phone)
        )
    else:
        cursor.execute(
            "SELECT role, content FROM chat_records "
            "WHERE session_id = %s AND phone IS NULL ORDER BY id DESC LIMIT 12",
            (session_id,)
        )
    history_records = list(cursor.fetchall())
    history_records.reverse()
    history_messages = [
        {"role": r["role"] if isinstance(r, dict) else r[0],
         "content": r["content"] if isinstance(r, dict) else r[1]}
        for r in history_records
    ]

    # 6. 调用 DeepSeek
    messages = build_messages(user_question, history_messages, dify_context, local_context)
    ai_reply = call_deepseek(messages)

    if "不可用" in ai_reply or "未配置" in ai_reply:
        if dify_context:
            return {"reply": dify_context[:900], "source": "dify"}
        if local_context:
            return {"reply": local_context[:900], "source": "local"}
        return {
            "reply": "您好！您可以问我：\n- 景区开放时间\n- 门票价格\n- 游览路线推荐",
            "source": "fallback"
        }

    return {"reply": ai_reply, "source": "dify" if dify_context else "ai"}


# ============================================================
# 历史会话查询
# ============================================================

def get_user_sessions(cursor, phone: str) -> list:
    cursor.execute(
        "SELECT session_id, MIN(created_at) as created_at "
        "FROM chat_records WHERE phone = %s "
        "GROUP BY session_id ORDER BY created_at DESC",
        (phone,)
    )
    sessions = cursor.fetchall()
    for s in sessions:
        cursor.execute(
            "SELECT content FROM chat_records "
            "WHERE session_id = %s AND phone = %s AND role = 'user' ORDER BY id ASC LIMIT 1",
            (s["session_id"] if isinstance(s, dict) else s[0], phone)
        )
        first = cursor.fetchone()
        if isinstance(s, dict):
            s["title"] = first["content"] if first else "新对话"
            s["created_at"] = (
                s["created_at"].isoformat()
                if isinstance(s["created_at"], datetime)
                else str(s["created_at"])
            )
    return sessions


def get_session_messages(cursor, session_id: str, phone: str = None) -> list:
    if phone:
        cursor.execute(
            "SELECT role, content, created_at FROM chat_records "
            "WHERE session_id = %s AND phone = %s "
            "ORDER BY id ASC",
            (session_id, phone)
        )
    else:
        cursor.execute(
            "SELECT role, content, created_at FROM chat_records "
            "WHERE session_id = %s AND phone IS NULL ORDER BY id ASC",
            (session_id,)
        )
    messages = cursor.fetchall()
    for m in messages:
        if isinstance(m, dict) and isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
    return messages
