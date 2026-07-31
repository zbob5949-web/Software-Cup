from fastapi import APIRouter
from app.database import get_db_connection

router = APIRouter()

def Result(code, msg, data=None):
    return {"code": code, "msg": msg, "data": data}

# 景区所有地名，只表示位置，不作为意图判断
LOCATION_WORDS = {
    "灵山大佛", "灵山", "拈花湾", "景区", "梵宫", "胜境",
    "祥符禅寺", "五印坛城", "九龙灌浴", "菩提大道",
    "灵山大照壁", "五明桥", "佛足坛", "五智门", "百子戏弥勒",
    "天下第一掌", "佛教文化博览馆", "曼飞龙塔", "无尽意斋",
    "拈花广场", "梵天花海", "香月花街", "拈花堂", "五灯湖", "鹿鸣谷",
    "降魔浮雕", "阿育王柱",
}

# 通用词，不作为有效命中
GENERIC_WORDS = {
    "多少钱", "多少", "价格", "怎么走", "如何", "什么", "哪里", "有吗",
    "几点", "开门", "关门", "电话", "联系方式", "预约", "预定",
    "请问", "你好", "可以", "吗", "呢", "啊", "不", "是", "的", "了",
    "我", "在", "想", "要", "去", "来", "就", "也", "都", "和", "时间",
}

# 合并黑名单
SKIP_WORDS = GENERIC_WORDS | LOCATION_WORDS


def _match_faq_smart(cursor, user_question: str):
    """
    三级匹配，返回 (faq_row, score)
    faq_row 为 dict 含 id/question/answer/category，或 None
    """
    if not user_question:
        return None, 0
    q = user_question.strip()

    # 1. 精确匹配
    cursor.execute("""
        SELECT id, question, answer, category FROM faqs
        WHERE is_active = TRUE AND question = %s LIMIT 1
    """, (q,))
    row = cursor.fetchone()
    if row:
        return row, 100

    # 2. 模糊匹配：FAQ问题 包含在 用户问题里，或 用户问题 包含在 FAQ问题里
    # 原来只做了一个方向，现在两个方向都做
    cursor.execute("""
        SELECT id, question, answer, category FROM faqs
        WHERE is_active = TRUE
        AND (
            question LIKE %s
            OR %s LIKE CONCAT('%%', question, '%%')
        )
        ORDER BY CHAR_LENGTH(question) DESC LIMIT 1
    """, (f"%{q}%", q))
    row = cursor.fetchone()
    if row:
        return row, 80

    # 3. 关键词匹配
    # 修复：不再强制第一个词为主题词，改为统计所有非黑名单词的命中数
    cursor.execute("""
        SELECT id, question, answer, category, keywords FROM faqs
        WHERE is_active = TRUE AND keywords IS NOT NULL
    """)
    best_match, best_score = None, 0

    for r in cursor.fetchall():
        keywords_raw = r.get("keywords") if isinstance(r, dict) else r[4]
        if not keywords_raw:
            continue

        keywords = [k.strip() for k in keywords_raw.replace(",", "，").split("，") if k.strip()]
        if not keywords:
            continue

        # 统计命中的有效关键词数（排除黑名单）
        valid_hits = [kw for kw in keywords if kw in q and kw not in SKIP_WORDS]
        score = len(valid_hits)

        if score > best_score:
            best_score = score
            best_match = r

    if best_match and best_score > 0:
        if isinstance(best_match, dict):
            return best_match, best_score
        else:
            return {
                "id": best_match[0],
                "question": best_match[1],
                "answer": best_match[2],
                "category": best_match[3],
            }, best_score

    return None, 0


# ---------- 接口 15：FAQ 列表 ----------
@router.get("/api/faqs")
def get_faqs(category: str = None):
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            if category:
                cursor.execute("""
                    SELECT id, question, answer, category FROM faqs
                    WHERE is_active = TRUE AND category = %s ORDER BY sort_order ASC
                """, (category,))
            else:
                cursor.execute("""
                    SELECT id, question, answer, category FROM faqs
                    WHERE is_active = TRUE ORDER BY sort_order ASC
                """)
            rows = cursor.fetchall()
            faqs = [{"id": r["id"], "question": r["question"],
                     "answer": r["answer"], "category": r["category"]} for r in rows]
        return Result(200, "success", {"faqs": faqs})
    except Exception as e:
        print(f"[faq 错误] {e}")
        return Result(50001, "获取FAQ失败")
    finally:
        conn.close()


# ---------- 接口 16：FAQ 智能匹配 ----------
@router.get("/api/faqs/match")
def match_faq(q: str = ""):
    if not q.strip():
        return Result(40001, "请输入问题")
    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败")
    try:
        with conn.cursor() as cursor:
            row, score = _match_faq_smart(cursor, q.strip())
            if row:
                return Result(200, "success", {
                    "matched": True,
                    "score": score,
                    "faq": {
                        "id": row["id"],
                        "question": row["question"],
                        "answer": row["answer"],
                        "category": row["category"],
                    }
                })
            return Result(200, "success", {"matched": False, "score": 0, "faq": None})
    except Exception as e:
        print(f"[faq match 错误] {e}")
        return Result(50001, "匹配失败")
    finally:
        conn.close()