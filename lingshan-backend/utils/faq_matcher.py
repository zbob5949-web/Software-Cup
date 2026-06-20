"""
共享 FAQ 匹配逻辑
chat_service 和faq管理后台共用此模块，FAQ管理后台调用 match_faq 函数，主要是为了让管理员测试新配置的FAQ是否能被正确匹配。
"""
from difflib import SequenceMatcher

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

SKIP_WORDS = GENERIC_WORDS | LOCATION_WORDS


def match_faq(cursor, user_question: str) -> list:
    """
    三级匹配，返回匹配结果列表
    每项为 dict: {id, question, answer, category, match_type, score}
    无匹配返回空列表
    """
    if not user_question:
        return []
    q = user_question.strip()

    # 1. 精确匹配
    cursor.execute(
        "SELECT id, question, answer, category FROM faqs WHERE is_active = 1 AND question = %s",
        (q,)
    )
    exact = cursor.fetchone()
    if exact:
        return [{"id": exact["id"], "question": exact["question"],
                 "answer": exact["answer"], "category": exact["category"],
                 "match_type": "exact", "score": 100}]

    # 2. 模糊匹配（双向）
    cursor.execute(
        """SELECT id, question, answer, category FROM faqs
           WHERE is_active = 1
           AND (question LIKE %s OR %s LIKE CONCAT('%%', question, '%%'))
           ORDER BY CHAR_LENGTH(question) DESC LIMIT 1""",
        (f"%{q}%", q)
    )
    fuzzy = cursor.fetchone()
    if fuzzy:
        return [{"id": fuzzy["id"], "question": fuzzy["question"],
                 "answer": fuzzy["answer"], "category": fuzzy["category"],
                 "match_type": "fuzzy", "score": 80}]

    # 3. 综合匹配：关键词命中 + 字符相似度。
    # 这样管理员新增FAQ后，不必把所有问法都写死；例如“票多少钱/门票价格/怎么买票”都能靠关键词和相似度召回。
    cursor.execute(
        "SELECT id, question, answer, category, keywords FROM faqs "
        "WHERE is_active = 1 AND keywords IS NOT NULL"
    )
    all_faqs = cursor.fetchall()
    candidates = []

    for faq in all_faqs:
        if isinstance(faq, dict):
            keywords_raw = faq["keywords"]
        else:
            keywords_raw = faq[4]
        if not keywords_raw:
            continue
        faq_question = faq["question"] if isinstance(faq, dict) else faq[1]
        keywords = [k.strip() for k in keywords_raw.replace(",", "，").split("，") if k.strip()]
        valid_hits = [kw for kw in keywords if kw in q and kw not in SKIP_WORDS]
        # SequenceMatcher 对中文短句可用，作为 FAQ 问法相近时的补充分数。
        similarity = SequenceMatcher(None, q, faq_question).ratio()
        keyword_score = sum(max(1, min(len(kw), 8)) for kw in valid_hits)
        score = keyword_score * 10 + int(similarity * 60)
        # 至少需要一个有效关键词，或问题相似度达到较高阈值，避免只因“哪里/多少”等泛词误命中。
        if valid_hits or similarity >= 0.62:
            candidates.append((score, faq, valid_hits, similarity))

    if not candidates:
        return []

    # 分数相同时，关键词越具体（越长）优先
    candidates.sort(
        key=lambda x: (
            x[0],
            len(x[2]),
            max((len(kw) for kw in (x[1]["keywords"] if isinstance(x[1], dict)
                 else x[1][4] or "").replace(",", "，").split("，") if kw.strip()), default=0),
        ),
        reverse=True
    )
    best_score, best_faq, valid_hits, similarity = candidates[0]
    match_type = "keyword" if valid_hits else "similarity"
    if isinstance(best_faq, dict):
        return [{"id": best_faq["id"], "question": best_faq["question"],
                 "answer": best_faq["answer"], "category": best_faq["category"],
                 "match_type": match_type, "score": best_score}]
    return [{"id": best_faq[0], "question": best_faq[1],
             "answer": best_faq[2], "category": best_faq[3],
             "match_type": match_type, "score": best_score}]
