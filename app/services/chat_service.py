import requests
from datetime import datetime
from app.core.config import DEEPSEEK_KEY, DIFY_API_KEY, DIFY_DATASET_ID, DIFY_API_BASE_URL
from app.services.weather_service import format_weather_reply, get_weather_data, is_weather_query
import logging

logger = logging.getLogger(__name__)

# 和 faq.py 保持一致的黑名单
LOCATION_WORDS = {
    "灵山大佛", "灵山", "拈花湾", "景区", "梵宫", "胜境",
    "祥符禅寺", "五印坛城", "九龙灌浴", "菩提大道",
    "灵山大照壁", "五明桥", "佛足坛", "五智门", "百子戏弥勒",
    "天下第一掌", "佛教文化博览馆", "曼飞龙塔", "无尽意斋",
    "拈花广场", "梵天花海", "香月花街", "拈花堂", "五灯湖", "鹿鸣谷",
    "降魔浮雕", "阿育王柱",
}
STOP_WORDS = {
    "请问", "你好", "可以", "吗", "呢", "啊", "不", "是", "的", "了",
    "我", "在", "想", "要", "去", "来", "就", "也", "都", "和",
}
SKIP_WORDS = STOP_WORDS | LOCATION_WORDS

INTENT_WORDS = {
    "门票", "票价", "价格", "多少钱", "多少", "费用", "优惠", "免票", "半价",
    "开放", "营业", "开门", "关门", "几点", "时间",
    "演出", "表演", "吉祥颂", "九龙灌浴",
    "路线", "规划", "游览", "怎么玩", "几小时", "半天", "一天",
    "厕所", "卫生间", "餐厅", "吃饭", "素斋", "观光车", "停车", "交通",
    "预约", "电话", "联系方式", "讲解", "导游",
    "历史", "文化", "介绍", "故事", "看点", "祈福",
}

SPOT_ALIASES = {
    "大佛": "灵山大佛",
    "佛": "灵山大佛",
    "梵宫": "灵山梵宫",
    "吉祥颂": "灵山梵宫 吉祥颂",
    "坛城": "五印坛城",
    "大照壁": "灵山大照壁",
    "照壁": "灵山大照壁",
    "禅寺": "祥符禅寺",
    "寺": "祥符禅寺",
    "九龙": "九龙灌浴",
    "灌浴": "九龙灌浴",
    "弥勒": "百子戏弥勒",
    "佛手": "天下第一掌",
    "第一掌": "天下第一掌",
    "阿育王": "阿育王柱",
    "曼飞龙": "曼飞龙塔",
    "博览馆": "佛教文化博览馆",
}


def expand_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    additions = ["灵山胜境"]
    for alias, canonical in SPOT_ALIASES.items():
        if alias in q and canonical not in q:
            additions.append(canonical)
    for word in INTENT_WORDS:
        if word in q:
            additions.append(word)
    seen = set()
    terms = []
    for term in [q, *additions]:
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    return " ".join(terms)


def compact_context(text: str, max_chars: int = 3600) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit("\n", 1)[0].strip()


# ============================================================
# FAQ 匹配（和 faq.py 逻辑一致，供 chat 流程内部使用）
# ============================================================

def match_faq(cursor, user_question: str) -> list:
    if not user_question:
        return []
    q = user_question.strip()

    # 1. 精确匹配
    cursor.execute(
        "SELECT id, question, answer FROM faqs WHERE is_active = 1 AND question = %s",
        (q,)
    )
    exact = cursor.fetchone()
    if exact:
        return [{"question": exact["question"], "answer": exact["answer"],
                 "match_type": "exact", "score": 100}]

    # 2. 模糊匹配（双向）
    cursor.execute(
        """SELECT id, question, answer FROM faqs
           WHERE is_active = 1
           AND (question LIKE %s OR %s LIKE CONCAT('%%', question, '%%'))
           ORDER BY CHAR_LENGTH(question) DESC LIMIT 1""",
        (f"%{q}%", q)
    )
    fuzzy = cursor.fetchone()
    if fuzzy:
        return [{"question": fuzzy["question"], "answer": fuzzy["answer"],
                 "match_type": "fuzzy", "score": 80}]

    # 3. 关键词匹配（所有关键词平等对待，不强制主题词）
    cursor.execute(
        "SELECT id, question, answer, keywords FROM faqs "
        "WHERE is_active = 1 AND keywords IS NOT NULL"
    )
    all_faqs = cursor.fetchall()
    candidates = []

    for faq in all_faqs:
        keywords_raw = faq.get("keywords") if isinstance(faq, dict) else faq[3]
        if not keywords_raw:
            continue
        keywords = [k.strip() for k in keywords_raw.replace(",", "，").split("，") if k.strip()]
        valid_hits = [kw for kw in keywords if kw in q and kw not in SKIP_WORDS]
        score = len(valid_hits)
        if score > 0:
            candidates.append((score, faq))

    if not candidates:
        return []

    # 分数相同时，关键词越具体（越长）优先
    candidates.sort(
        key=lambda x: (
            x[0],
            max((len(kw) for kw in (x[1].get("keywords", "") if isinstance(x[1], dict)
                 else x[1][3] or "").replace(",", "，").split("，") if kw.strip()), default=0)
        ),
        reverse=True
    )
    best_score, best_faq = candidates[0]
    if isinstance(best_faq, dict):
        return [{"question": best_faq["question"], "answer": best_faq["answer"],
                 "match_type": "keyword", "score": best_score}]
    return [{"question": best_faq[1], "answer": best_faq[2],
             "match_type": "keyword", "score": best_score}]


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
        url = f"{DIFY_API_BASE_URL}/v1/datasets/{DIFY_DATASET_ID}/retrieve"
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json"
        }
        search_query = expand_query(query)
        body = {
            "query": search_query,
            "retrieval_model": {
                "search_method": "hybrid_search",
                "top_k": 8,
                "reranking_enable": False,
                "score_threshold_enabled": False
            }
        }
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        if resp.status_code == 200:
            records = resp.json().get("records", [])
            if records:
                contents = []
                for record in records[:5]:
                    segment = record.get("segment") or {}
                    content = segment.get("content") or record.get("content") or ""
                    if content.strip():
                        score = record.get("score")
                        score_text = f" score={score:.4f}" if isinstance(score, (int, float)) else ""
                        contents.append(f"[Dify{score_text}]\n{content.strip()}")
                logger.info("Dify retrieve hit: query=%s expanded=%s records=%s", query, search_query, len(records))
                return compact_context("\n\n".join(contents))
        elif resp.status_code == 401:
            logger.error("Dify retrieve unauthorized: check DIFY_API_KEY and DIFY_DATASET_ID permissions")
        else:
            logger.warning("Dify retrieve failed: status=%s body=%s", resp.status_code, resp.text[:500])
        return ""
    except Exception as exc:
        logger.exception("Dify retrieve exception: %s", exc)
        return ""


def retrieve_from_local_knowledge(cursor, query: str) -> str:
    if not query:
        return ""

    contents = []
    expanded_query = expand_query(query)
    try:
        cursor.execute(
            "SELECT name, category, description, open_time, duration, tips "
            "FROM spots WHERE is_active = 1 ORDER BY sort_order ASC"
        )
        spots = cursor.fetchall()
        matched_spots = []
        for spot in spots:
            name = spot["name"] if isinstance(spot, dict) else spot[0]
            category = spot["category"] if isinstance(spot, dict) else spot[1]
            description = spot["description"] if isinstance(spot, dict) else spot[2]
            open_time = spot["open_time"] if isinstance(spot, dict) else spot[3]
            duration = spot["duration"] if isinstance(spot, dict) else spot[4]
            tips = spot["tips"] if isinstance(spot, dict) else spot[5]
            haystack = f"{name} {category or ''} {description or ''} {open_time or ''} {duration or ''} {tips or ''}"
            score = 0
            if name in expanded_query:
                score += 5
            if category and category in expanded_query and category not in SKIP_WORDS:
                score += 2
            score += sum(1 for word in INTENT_WORDS if word in expanded_query and word in haystack)
            if score > 0:
                matched_spots.append((score, spot))

        matched_spots.sort(key=lambda item: item[0], reverse=True)
        for _, spot in matched_spots[:4]:
            name = spot["name"] if isinstance(spot, dict) else spot[0]
            category = spot["category"] if isinstance(spot, dict) else spot[1]
            description = spot["description"] if isinstance(spot, dict) else spot[2]
            open_time = spot["open_time"] if isinstance(spot, dict) else spot[3]
            duration = spot["duration"] if isinstance(spot, dict) else spot[4]
            tips = spot["tips"] if isinstance(spot, dict) else spot[5]
            contents.append(
                f"[本地景点]\n"
                f"景点：{name}\n"
                f"分类：{category or '未分类'}\n"
                f"开放时间：{open_time or '暂无'}\n"
                f"建议游览：{duration or '暂无'}\n"
                f"介绍：{description or '暂无'}\n"
                f"提示：{tips or '暂无'}"
            )

        route_words = ("路线", "规划", "游览", "怎么玩", "几小时", "半天", "一天")
        if any(word in expanded_query for word in route_words):
            cursor.execute(
                "SELECT name, duration, difficulty, description, spot_ids "
                "FROM routes WHERE is_active = 1 ORDER BY hours_min ASC, hours_max ASC LIMIT 3"
            )
            routes = cursor.fetchall()
            for route in routes:
                name = route["name"] if isinstance(route, dict) else route[0]
                duration = route["duration"] if isinstance(route, dict) else route[1]
                difficulty = route["difficulty"] if isinstance(route, dict) else route[2]
                description = route["description"] if isinstance(route, dict) else route[3]
                spot_ids = route["spot_ids"] if isinstance(route, dict) else route[4]
                contents.append(
                    f"[本地路线]\n"
                    f"路线：{name}\n"
                    f"时长：{duration or '暂无'}\n"
                    f"难度：{difficulty or '暂无'}\n"
                    f"景点顺序：{spot_ids or '暂无'}\n"
                    f"说明：{description or '暂无'}"
                )
    except Exception as exc:
        logger.exception("Local knowledge retrieve exception: %s", exc)
        return ""

    return compact_context("\n\n".join(contents[:6]), max_chars=2600)


# ============================================================
# 构造 messages
# ============================================================

def build_messages(question: str, history: list = None, dify_context: str = None) -> list:
    """
    重写系统提示：明确意图判断优先级
    参考 database.py 里的景区完整数据，让 AI 知道景区有哪些服务设施
    """
    system_prompt = """你是灵山景区智能助手"灵小佑"。

灵山胜境景区包含以下区域：
- 灵山胜境主景区：灵山大佛、九龙灌浴、灵山梵宫、五印坛城、祥符禅寺、菩提大道等
- 拈花湾禅意小镇：拈花广场、梵天花海、香月花街、拈花堂、五灯湖、鹿鸣谷等
- 景区内设有餐厅（梵宫素斋50元/位、素面35元/位）、观光车服务（40元/人）、导游讲解（300元起）

【回答规则】：
1. 如果提供了"知识库补充参考"，必须优先根据参考内容回答，不要凭空编造。
2. 参考内容中有票价、时间、路线、演出场次等结构化信息时，直接给出关键信息。
3. 参考内容不足时，先说明"我目前只查到这些信息"，再给出合理建议或追问。

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
→ 详细准确地回答景区相关问题

回答热情、准确、简洁，不超过200字。遇到不确定的情况先问清楚游客需要什么。"""

    if dify_context:
        system_prompt += f"\n\n【知识库补充参考，优先使用】：\n{dify_context}"

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": question})
    return messages


# ============================================================
# 消息持久化
# ============================================================

def save_message(cursor, session_id: str, phone: str, role: str, content: str, source: str | None = None):
    cursor.execute(
        "INSERT INTO chat_records (session_id, phone, role, content, source, created_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (session_id, phone, role, content, source, datetime.now())
    )


def cleanup_old_records(cursor, session_id: str, max_records: int = 20):
    cursor.execute(
        "SELECT id FROM chat_records WHERE session_id = %s ORDER BY id DESC LIMIT 1 OFFSET %s",
        (session_id, max_records)
    )
    old = cursor.fetchone()
    if old:
        old_id = old["id"] if isinstance(old, dict) else old[0]
        cursor.execute(
            "DELETE FROM chat_records WHERE session_id = %s AND id < %s",
            (session_id, old_id)
        )


# ============================================================
# 核心对话处理
# ============================================================

def process_user_chat_without_db(user_question: str) -> dict:
    """
    数据库不可用时的对话处理：直接走 Dify 知识库 → DeepSeek。
    不做 FAQ 匹配、不查本地景点库、不保存历史记录。
    这是保证 Dify 知识库始终生效的关键路径。
    """
    # 1. Dify 知识库检索（始终执行，这是用户的核心需求）
    dify_context = retrieve_from_dify(user_question) if DIFY_API_KEY and DIFY_DATASET_ID else ""

    source = "ai"
    if dify_context:
        source = "dify"

    # 2. 天气快速通道
    if is_weather_query(user_question):
        weather_data = get_weather_data()
        return {"reply": format_weather_reply(weather_data), "source": "weather"}

    # 3. 构建上下文
    context_parts = []
    if dify_context:
        context_parts.append(dify_context)

    # 附带实时天气
    weather_data = get_weather_data()
    if not weather_data.get("error"):
        context_parts.append(
            f"[实时天气]\n"
            f"城市：{weather_data.get('city', '无锡灵山')}\n"
            f"天气：{weather_data.get('weather', '未知')}\n"
            f"温度：{weather_data.get('temperature', '--')}\n"
            f"建议：{weather_data.get('advice', '')}"
        )

    combined_context = compact_context("\n\n".join(context_parts), max_chars=5200)
    logger.info(
        "Chat context (no-db): source=%s question=%s context_chars=%s",
        source, user_question, len(combined_context)
    )

    # 4. 构建 messages 并调用 DeepSeek
    messages = build_messages(user_question, history=None, dify_context=combined_context)
    ai_reply = call_deepseek(messages)

    if "不可用" in ai_reply or "未配置" in ai_reply:
        return {
            "reply": "您好！您可以问我：\n- 景区开放时间\n- 门票价格\n- 游览路线推荐\n- 景点历史文化",
            "source": "fallback"
        }

    return {"reply": ai_reply, "source": source}


def process_user_chat(cursor, user_question: str, session_id: str,
                      phone: str = None) -> dict:
    if is_weather_query(user_question):
        weather_data = get_weather_data()
        return {"reply": format_weather_reply(weather_data), "source": "weather"}

    # 1. FAQ 精确/强模糊匹配。弱关键词匹配不直接抢答，避免压过知识库。
    faq_matches = match_faq(cursor, user_question)
    if faq_matches and faq_matches[0].get("score", 0) >= 80:
        best = faq_matches[0]
        return {"reply": best["answer"], "source": "faq"}

    # 2. Dify 知识库检索
    context_parts = []
    source = "ai"
    dify_context = retrieve_from_dify(user_question) if DIFY_API_KEY and DIFY_DATASET_ID else ""
    if dify_context:
        context_parts.append(dify_context)
        source = "dify"

    local_context = retrieve_from_local_knowledge(cursor, user_question)
    if local_context:
        context_parts.append(local_context)
        if source == "dify":
            source = "dify+local"
        elif source == "ai":
            source = "local"

    if faq_matches:
        best = faq_matches[0]
        context_parts.append(f"[FAQ弱匹配 score={best.get('score', 0)}]\n问题：{best['question']}\n答案：{best['answer']}")
        if source == "ai":
            source = "faq_keyword"
        else:
            source = f"{source}+faq_keyword"

    # 始终附带实时天气数据，供 AI 在回答中参考（天气快速通道未命中时）
    weather_data = get_weather_data()
    if not weather_data.get("error"):
        context_parts.append(
            f"[实时天气]\n"
            f"城市：{weather_data.get('city', '无锡灵山')}\n"
            f"天气：{weather_data.get('weather', '未知')}\n"
            f"温度：{weather_data.get('temperature', '--')}\n"
            f"建议：{weather_data.get('advice', '')}"
        )

    dify_context = compact_context("\n\n".join(context_parts), max_chars=5200)
    logger.info(
        "Chat context selected: source=%s question=%s context_chars=%s",
        source, user_question, len(dify_context)
    )

    # 3. 获取会话历史（最近6轮）
    cursor.execute(
        "SELECT role, content FROM chat_records "
        "WHERE session_id = %s ORDER BY id DESC LIMIT 12",
        (session_id,)
    )
    history_records = cursor.fetchall()
    history_records.reverse()
    history_messages = [
        {"role": r["role"] if isinstance(r, dict) else r[0],
         "content": r["content"] if isinstance(r, dict) else r[1]}
        for r in history_records
    ]
    if history_messages and history_messages[-1]["role"] == "user" and history_messages[-1]["content"] == user_question:
        history_messages.pop()

    # 4. 调用 DeepSeek
    messages = build_messages(user_question, history_messages, dify_context)
    ai_reply = call_deepseek(messages)

    if "不可用" in ai_reply or "未配置" in ai_reply:
        return {
            "reply": "您好！您可以问我：\n- 景区开放时间\n- 门票价格\n- 游览路线推荐",
            "source": "fallback"
        }

    return {"reply": ai_reply, "source": source}


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
            "WHERE session_id = %s AND role = 'user' ORDER BY id ASC LIMIT 1",
            (s["session_id"] if isinstance(s, dict) else s[0],)
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
            "WHERE session_id = %s AND (phone = %s OR role = 'assistant') "
            "ORDER BY id ASC",
            (session_id, phone)
        )
    else:
        cursor.execute(
            "SELECT role, content, created_at FROM chat_records "
            "WHERE session_id = %s ORDER BY id ASC",
            (session_id,)
        )
    messages = cursor.fetchall()
    for m in messages:
        if isinstance(m, dict) and isinstance(m.get("created_at"), datetime):
            m["created_at"] = m["created_at"].isoformat()
    return messages
