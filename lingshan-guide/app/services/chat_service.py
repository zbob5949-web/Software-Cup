import requests
from datetime import datetime
from app.core.config import DEEPSEEK_KEY, DIFY_API_KEY, DIFY_DATASET_ID
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
GENERIC_WORDS = {
    "多少钱", "多少", "价格", "怎么走", "如何", "什么", "哪里", "有吗",
    "几点", "开门", "关门", "电话", "联系方式", "预约", "预定",
    "请问", "你好", "可以", "吗", "呢", "啊", "不", "是", "的", "了",
    "我", "在", "想", "要", "去", "来", "就", "也", "都", "和", "时间",
}
SKIP_WORDS = GENERIC_WORDS | LOCATION_WORDS


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
        url = f"https://api.dify.ai/v1/datasets/{DIFY_DATASET_ID}/retrieve"
        headers = {
            "Authorization": f"Bearer {DIFY_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {"query": query, "retrieval_model": {"search_method": "hybrid"}}
        resp = requests.post(url, json=body, headers=headers, timeout=10)
        if resp.status_code == 200:
            records = resp.json().get("records", [])
            if records:
                return "\n\n".join(r.get("content", "") for r in records[:3])
        return ""
    except Exception:
        return ""


# ============================================================
# 构造 messages
# ============================================================

def build_messages(question: str, history: list = None, dify_context: str = None) -> list:
    """
    重写 system prompt：明确意图判断优先级
    参考 database.py 里的景区完整数据，让 AI 知道景区有哪些服务设施
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
→ 详细准确地回答景区相关问题

回答热情、准确、简洁，不超过200字。遇到不确定的情况先问清楚游客需要什么。"""

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

def save_message(cursor, session_id: str, phone: str, role: str, content: str):
    cursor.execute(
        "INSERT INTO chat_records (session_id, phone, role, content, created_at) VALUES (%s, %s, %s, %s, %s)",
        (session_id, phone, role, content, datetime.now())
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

def process_user_chat(cursor, user_question: str, session_id: str,
                      phone: str = None) -> dict:
    # 1. FAQ 精准匹配
    faq_matches = match_faq(cursor, user_question)
    if faq_matches:
        best = faq_matches[0]
        return {"reply": best["answer"], "source": "faq"}

    # 2. Dify 知识库检索
    dify_context = retrieve_from_dify(user_question) if DIFY_API_KEY and DIFY_DATASET_ID else ""

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

    # 4. 调用 DeepSeek
    messages = build_messages(user_question, history_messages, dify_context)
    ai_reply = call_deepseek(messages)

    if "不可用" in ai_reply or "未配置" in ai_reply:
        return {
            "reply": "您好！您可以问我：\n- 景区开放时间\n- 门票价格\n- 游览路线推荐",
            "source": "fallback"
        }

    return {"reply": ai_reply, "source": "ai"}


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