import requests
import re
from datetime import datetime
from app.core.config import DEEPSEEK_KEY
from app.services.weather_service import format_weather_reply, get_weather_data, is_weather_query
import logging

logger = logging.getLogger(__name__)

# Bypass the broken localhost proxy for direct Dify access.
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_direct_session = requests.Session()
_direct_session.trust_env = False
# 连接池复用：避免每次请求重新建立 TCP/TLS 连接
_adapter = HTTPAdapter(
    pool_connections=4,
    pool_maxsize=8,
    max_retries=Retry(total=1, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]),
)
_direct_session.mount("http://", _adapter)
_direct_session.mount("https://", _adapter)

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


def clean_ai_reply(text: str) -> str:
    """Remove markdown separators and dash-heavy list formatting from chat output."""
    lines = []
    for raw_line in (text or '').replace('\r\n', '\n').split('\n'):
        line = raw_line.strip()
        if not line or all(char in '-_* ' for char in line):
            continue
        line = __import__('re').sub(r'^[-*]+\s+', '· ', line)
        lines.append(line)
    return '\n'.join(lines).strip()


def compact_context(text: str, max_chars: int = 3600) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit("\n", 1)[0].strip()


# ============================================================
# FAQ 匹配（和 faq.py 逻辑一致，供 chat 流程内部使用）
# ============================================================

# ── 内存 FAQ 快速查找表（启动时加载，O(1) 精确命中）──
_faq_exact_map: dict[str, str] = {}
_faq_loaded: bool = False


def _ensure_faq_cache(cursor) -> None:
    """首次调用时从 DB 加载所有 FAQ 到内存哈希表"""
    global _faq_loaded, _faq_exact_map
    if _faq_loaded:
        return
    try:
        cursor.execute("SELECT id, question, answer FROM faqs WHERE is_active = 1")
        rows = cursor.fetchall()
        for faq in rows:
            q = re.sub(r"[\s　，。？！!?、：；‘'""（）()【】《》]", "",
                       (faq["question"] if isinstance(faq, dict) else faq[1]).strip().lower())
            a = faq["answer"] if isinstance(faq, dict) else faq[2]
            if q:
                _faq_exact_map[q] = a
        _faq_loaded = True
        logger.info("FAQ cache loaded: %d entries", len(_faq_exact_map))
    except Exception:
        _faq_loaded = True  # 失败也标记，避免反复尝试


def _fast_faq_lookup(question: str) -> str | None:
    """O(1) 内存哈希查 FAQ，不查 DB"""
    if not _faq_loaded:
        return None
    q = re.sub(r"[\s　，。？！!?、：；‘'""（）()【】《》]", "", question.strip().lower())
    return _faq_exact_map.get(q)


def match_faq(cursor, user_question: str) -> list:
    if not user_question:
        return []

    # 0. 内存快速命中（O(1)，无需DB）
    cached = _fast_faq_lookup(user_question)
    if cached:
        return [{"question": user_question, "answer": cached, "match_type": "exact", "score": 100}]

    # 前端会把兴趣偏好作为上下文前缀传入，先移除它，避免破坏 FAQ 精确命中。
    q = re.sub(r"^\[[^\]]+\]\s*", "", user_question.strip())

    def normalize(text: str) -> str:
        return re.sub(r"[\s\u3000，。？！!?、：；‘’“”\"'（）()【】\[\]《》<>.,:;]", "", text.lower())

    q_norm = normalize(q)
    if not q_norm:
        return []

    cursor.execute("SELECT id, question, answer, keywords FROM faqs WHERE is_active = 1")
    rows = cursor.fetchall()
    candidates = []

    for faq in rows:
        if isinstance(faq, dict):
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            keywords_raw = faq.get("keywords") or ""
        else:
            question, answer, keywords_raw = faq[1], faq[2], faq[3] or ""

        faq_norm = normalize(question)
        if not faq_norm:
            continue

        # 标准测试集常见的“请问/景区/多少钱”等变体也视为高置信命中。
        if faq_norm == q_norm:
            return [{"question": question, "answer": answer,
                     "match_type": "exact", "score": 100}]
        if len(q_norm) >= 4 and (q_norm in faq_norm or faq_norm in q_norm):
            candidates.append((92, len(faq_norm), question, answer, "fuzzy", []))
            continue

        keywords = [k.strip() for k in keywords_raw.replace(",", "，").split("，") if k.strip()]
        hits = [kw for kw in keywords if kw not in STOP_WORDS and normalize(kw) in q_norm]
        # 长关键词覆盖短关键词，避免“开放时间”同时重复计入“开放”和“时间”。
        hits = sorted(set(hits), key=lambda value: len(normalize(value)), reverse=True)
        distinct_hits = []
        for hit in hits:
            if not any(normalize(hit) in normalize(other) for other in distinct_hits):
                distinct_hits.append(hit)
        if not distinct_hits:
            continue
        longest = max(len(normalize(kw)) for kw in distinct_hits)
        score = 45 + sum(min(30, len(normalize(kw)) * 6) for kw in distinct_hits)
        if longest >= 4:
            score += 12
        if len(distinct_hits) >= 2:
            score += 12
        candidates.append((min(89, score), longest, question, answer, "keyword", distinct_hits))

    if not candidates:
        return []

    candidates.sort(key=lambda item: (item[0], item[1], len(item[5])), reverse=True)
    score, _, question, answer, match_type, hits = candidates[0]
    return [{"question": question, "answer": answer, "match_type": match_type,
             "score": score, "matched_keywords": hits}]

# ============================================================
# DeepSeek 调用
# ============================================================

# ── 高频问题缓存（避免重复调用 DeepSeek，降低延迟 <1s）──
_qa_cache: dict[str, str] = {}
_dify_cache: dict[str, str] = {}
CACHE_MAX_SIZE = 64


def _cache_key(question: str) -> str:
    """归一化作为缓存键"""
    return re.sub(r"[\s　，。？！!?、：；‘'""（）()【】《》]", "", question.strip().lower())


def call_deepseek(messages: list) -> str:
    if not DEEPSEEK_KEY:
        return "AI服务未配置，请联系管理员"

    # 检查缓存（用户问题在 messages[-1]["content"]）
    user_q = messages[-1]["content"] if messages else ""
    cache_hit = _qa_cache.get(_cache_key(user_q))
    if cache_hit:
        logger.info("DeepSeek cache hit: %s", user_q[:30])
        return cache_hit

    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,          # 进一步降低随机性，加速生成
            "max_tokens": 120,           # 系统提示要求不超150字，120 token足够
            "stream": False
        }
        resp = _direct_session.post(
            "https://api.deepseek.com/v1/chat/completions",
            json=payload, headers=headers, timeout=(0.5, 4.5)
        )
        if resp.status_code == 200:
            raw = resp.json()["choices"][0]["message"]["content"]
            reply = clean_ai_reply(raw)

            # 写入缓存
            if len(_qa_cache) >= CACHE_MAX_SIZE:
                _qa_cache.pop(next(iter(_qa_cache)))
            _qa_cache[_cache_key(user_q)] = reply
            return reply

        return "大模型暂时不可用，请稍后再试"
    except Exception:
        return "服务异常，请重试"


# ============================================================
# 本地向量知识库检索（替代 Dify）
# ============================================================

def retrieve_from_dify(query: str) -> str:
    """使用本地 ChromaDB vector store 进行语义检索，替代 Dify API。"""
    # 缓存命中
    cache_hit = _dify_cache.get(_cache_key(query))
    if cache_hit:
        logger.info("LocalKB cache hit: %s", query[:30])
        return cache_hit

    try:
        from app.services.vector_store import retrieve_formatted, collection_exists

        if not collection_exists():
            logger.warning("Vector index not built yet, returning empty")
            return ""

        result = retrieve_formatted(query, top_k=3)
        if result:
            if len(_dify_cache) >= CACHE_MAX_SIZE:
                _dify_cache.pop(next(iter(_dify_cache)))
            _dify_cache[_cache_key(query)] = result
            logger.info("LocalKB retrieve: query=%s result_chars=%d", query[:30], len(result))
            return result
        else:
            logger.info("LocalKB retrieve: no results above threshold for '%s'", query[:30])
            return ""
    except Exception as exc:
        logger.warning("LocalKB retrieve error: %s", exc)
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
    system_prompt = """你是灵山景区助手"灵小佑"，是一位热情、专业的景区导游。请严格遵循以下规则：

1. 如果提供的【知识库参考】中有相关信息，**必须严格依据知识库内容回答**，不要编造。
2. 如果没有找到相关信息，请根据景区背景常识热情地回答，如果确实不知道，请引导游客咨询景区工作人员。
3. 回答要简洁热情，不超过150字。
4. 优先处理游客的即时需求：厕所、餐厅、医疗、走失等。
5. 涉及时间、价格的回答要提醒以景区当天公告为准。
6. 回答中请使用"到"或"至"表示范围（如"3到5小时"），不要使用短横线"-"或波浪号"~"，避免语音播报错误。
7. **严禁**在回答中出现"知识库"、"资料库"、"数据库"、"系统提示"等后台术语，用自然的导游口吻回答。

景区背景常识（仅当知识库无相关内容时参考）：
- 灵山大佛：高88米的露天青铜释迦牟尼立像，灵山胜境核心地标
- 梵宫：佛教文化艺术殿堂，内有穹顶壁画木雕，《吉祥颂》演出场地
- 九龙灌浴：大型动态音乐群雕，再现佛祖诞生场景
- 五印坛城：藏传佛教风格建筑，展示藏文化
- 祥符禅寺：千年古刹，灵山历史的见证
- 天下第一掌：按灵山大佛右手复制，供游客摸佛手祈福
- 百子戏弥勒：大型青铜雕塑，弥勒佛与孩童嬉戏场景
- 登云道：216级台阶通往大佛脚下，寓意消除108种烦恼、实现108个愿望
- 门票：旺季（3-11月）210元，淡季120元，具体以景区公告为准
- 开放时间：7:00-17:30（夏季），7:30-17:00（冬季）
- 景区内交通：观光车30元/人"""

    if dify_context:
        system_prompt += f"\n\n【景区参考资料 — 请优先使用以下信息回答】：\n{dify_context}"

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
    dify_context = retrieve_from_dify(user_question)

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
            "reply": "您好！您可以问我：\n· 景区开放时间\n· 门票价格\n· 游览路线推荐\n· 景点历史文化",
            "source": "fallback"
        }

    return {"reply": clean_ai_reply(ai_reply), "source": source}


def process_user_chat(cursor, user_question: str, session_id: str,
                      phone: str = None) -> dict:
    if is_weather_query(user_question):
        weather_data = get_weather_data()
        return {"reply": format_weather_reply(weather_data), "source": "weather"}

    # 0. 内存FAQ快速命中（首次调用加载缓存，后续O(1)命中）
    _ensure_faq_cache(cursor)
    fast = _fast_faq_lookup(user_question)
    if fast:
        return {"reply": fast, "source": "faq"}

    # 1. FAQ 匹配：仅精确命中(100)直接返回；其余作为补充上下文喂给 Dify+LLM
    faq_matches = match_faq(cursor, user_question)
    if faq_matches and faq_matches[0].get("score", 0) >= 100:
        best = faq_matches[0]
        return {"reply": best["answer"], "source": "faq"}

    # 2. Dify 知识库检索（始终执行，是回答准确度的核心）
    context_parts = []
    source = "ai"
    dify_context = retrieve_from_dify(user_question)
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

    # FAQ 匹配作为补充上下文（非精确匹配时）
    if faq_matches and dify_context:
        # 有 Dify 结果时 FAQ 降级为弱参考，列在最后
        best = faq_matches[0]
        if best.get("score", 0) >= 80:
            context_parts.append(f"[FAQ命中 score={best.get('score', 0)}，仅供参考]\n{best['answer']}")
        elif best.get("score", 0) >= 45:
            context_parts.append(f"[FAQ弱匹配 score={best.get('score', 0)}]\n{best['answer']}")
    elif faq_matches:
        best = faq_matches[0]
        context_parts.append(f"[FAQ弱匹配 score={best.get('score', 0)}]\n问题：{best['question']}\n答案：{best['answer']}")
        if source == "ai":
            source = "faq_keyword"

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
    history_records = list(cursor.fetchall())
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

    if any(flag in ai_reply for flag in ("不可用", "未配置", "服务异常", "请重试", "暂时不可用")) and faq_matches:
        return {"reply": faq_matches[0]["answer"], "source": "faq_fallback"}

    if any(flag in ai_reply for flag in ("不可用", "未配置", "服务异常", "请重试", "暂时不可用")):
        return {
            "reply": "您好！您可以问我：\n· 景区开放时间\n· 门票价格\n· 游览路线推荐",
            "source": "fallback"
        }

    return {"reply": clean_ai_reply(ai_reply), "source": source}


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
