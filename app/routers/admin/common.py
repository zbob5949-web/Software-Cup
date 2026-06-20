from collections import Counter
from datetime import date, datetime
from difflib import SequenceMatcher
import re

from app.utils.faq_matcher import GENERIC_WORDS, LOCATION_WORDS
from app.utils.response import Result


def ok(data=None, msg="success"):
    return Result(200, msg, data)


def date_to_str(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def extract_hot_keywords(texts: list[str], limit: int = 10) -> list[dict]:
    stop = GENERIC_WORDS | LOCATION_WORDS | {"请问", "一下", "这个", "那个", "介绍", "推荐"}
    counter = Counter()
    for text in texts:
        for token in re.findall(r"[\u4e00-\u9fa5]{2,8}", text or ""):
            if token not in stop:
                counter[token] += 1
        for word in ["门票", "开放时间", "演出", "路线", "厕所", "餐厅", "停车", "梵宫", "灵山大佛", "拈花湾"]:
            if word in (text or ""):
                counter[word] += 2
    return [{"keyword": k, "count": v} for k, v in counter.most_common(limit)]


QUESTION_INTENT_RULES = [
    ("门票/票价/购票", ("门票", "票价", "多少钱", "价格", "成人票", "儿童票", "学生票", "老人票", "优惠", "免票", "半价", "购票", "买票", "联票")),
    ("演出时间/表演安排", ("演出", "表演", "几点演", "时间表", "吉祥颂", "九龙灌浴", "禅行", "灯光秀", "开园仪式")),
    ("开放时间/入园时间", ("开放时间", "开门", "关门", "几点开", "几点关", "营业时间", "闭园", "入园", "最晚入园")),
    ("路线推荐/游览规划", ("路线", "推荐", "规划", "怎么玩", "游览", "一日游", "半日游", "几个小时", "小时", "顺序", "先去", "适合老人", "亲子")),
    ("厕所/卫生间", ("厕所", "卫生间", "洗手间", " restroom", "WC", "wc")),
    ("餐饮/素斋/美食", ("吃饭", "餐厅", "美食", "素斋", "素面", "饿", "喝茶", "咖啡", "小吃")),
    ("交通/停车/观光车", ("停车", "停车场", "自驾", "公交", "地铁", "打车", "交通", "怎么去", "观光车", "电瓶车", "景交", "坐车")),
    ("位置导航/迷路指引", ("怎么走", "在哪里", "在哪", "位置", "导航", "迷路", "找不到", "方向", "附近")),
    ("祈福/礼佛体验", ("祈福", "拜佛", "烧香", "许愿", "抱佛脚", "摸掌", "撞钟", "转经筒", "开光")),
    ("天气/游玩建议", ("天气", "下雨", "热不热", "冷不冷", "穿什么", "带伞", "防晒")),
    ("数字人身份/使用帮助", ("你是谁", "叫什么", "能做什么", "功能", "怎么用", "帮助")),
    ("投诉/反馈/满意度", ("投诉", "反馈", "建议", "不满意", "满意", "差评", "好评", "服务态度")),
]


SPOT_SEMANTIC_WORDS = {
    "灵山大佛": ("灵山大佛", "大佛", "佛脚", "抱佛脚", "登云道"),
    "灵山梵宫": ("灵山梵宫", "梵宫", "吉祥颂", "东方卢浮宫"),
    "九龙灌浴": ("九龙灌浴", "九龙", "灌浴", "圣水"),
    "五印坛城": ("五印坛城", "坛城", "转经筒", "小布达拉宫"),
    "祥符禅寺": ("祥符禅寺", "禅寺", "寺庙", "撞钟"),
    "百子戏弥勒": ("百子戏弥勒", "弥勒", "弥勒佛"),
    "天下第一掌": ("天下第一掌", "佛手", "第一掌", "摸掌"),
    "佛教文化博览馆": ("佛教文化博览馆", "博览馆", "万佛殿"),
    "灵山大照壁": ("灵山大照壁", "大照壁", "照壁"),
    "菩提大道": ("菩提大道", "菩提树"),
    "五明桥": ("五明桥",),
    "佛足坛": ("佛足坛", "佛足印", "佛足"),
    "五智门": ("五智门",),
    "拈花湾": ("拈花湾", "禅意小镇"),
    "拈花广场": ("拈花广场", "拈花微笑"),
    "梵天花海": ("梵天花海", "花海"),
    "香月花街": ("香月花街", "花街"),
    "拈花堂": ("拈花堂",),
    "五灯湖": ("五灯湖", "禅行", "灯光秀"),
    "鹿鸣谷": ("鹿鸣谷",),
}


SYNONYM_REPLACEMENTS = {
    "票价": "门票",
    "价格": "门票",
    "多少钱": "门票",
    "买票": "购票",
    "厕所": "卫生间",
    "洗手间": "卫生间",
    "电瓶车": "观光车",
    "景交": "观光车",
    "表演": "演出",
    "营业时间": "开放时间",
    "开门": "开放时间",
    "关门": "开放时间",
    "怎么玩": "路线",
}


SERVICE_INTENT_LABELS = {"厕所/卫生间", "餐饮/素斋/美食", "交通/停车/观光车", "天气/游玩建议", "投诉/反馈/满意度"}


def _clean_question_text(text: str) -> str:
    value = (text or "").strip()
    for old, new in SYNONYM_REPLACEMENTS.items():
        value = value.replace(old, new)
    value = re.sub(r"[，。！？、,.!?；;：:\s\"'“”‘’（）()【】\[\]{}<>《》]", "", value)
    for word in ["请问", "你好", "您好", "一下", "这个", "那个", "我想", "想问", "可以", "吗", "呢"]:
        value = value.replace(word, "")
    return value[:80]


def _first_intent_label(text: str) -> str | None:
    for label, keywords in QUESTION_INTENT_RULES:
        if any(keyword in text for keyword in keywords):
            return label
    return None


def _semantic_signature(text: str) -> tuple[str, str]:
    q = _clean_question_text(text)
    raw = text or ""
    first_label = _first_intent_label(raw)
    if first_label in SERVICE_INTENT_LABELS:
        return f"intent:{first_label}", first_label
    for spot_name, aliases in SPOT_SEMANTIC_WORDS.items():
        if any(alias in raw for alias in aliases):
            if first_label:
                return f"{spot_name}:{first_label}", f"{spot_name} - {first_label}"
            return f"{spot_name}:景点讲解", f"{spot_name} - 景点讲解"
    if first_label:
        return f"intent:{first_label}", first_label
    return f"text:{q}", q or "其他问题"


def semantic_cluster_questions(texts: list[str], limit: int = 10) -> list[dict]:
    clusters: list[dict] = []
    for text in texts:
        if not text or not text.strip():
            continue
        key, label = _semantic_signature(text)
        normalized = _clean_question_text(text)
        target = None
        for cluster in clusters:
            if cluster["key"] == key:
                target = cluster
                break
            if key.startswith("text:") and cluster["key"].startswith("text:"):
                ratio = SequenceMatcher(None, normalized, cluster["normalized"]).ratio()
                if ratio >= 0.68:
                    target = cluster
                    break
        if target is None:
            target = {
                "key": key,
                "semantic_label": label,
                "normalized": normalized,
                "count": 0,
                "raw_counter": Counter(),
                "examples": [],
            }
            clusters.append(target)
        target["count"] += 1
        target["raw_counter"][text] += 1
        if text not in target["examples"] and len(target["examples"]) < 3:
            target["examples"].append(text)
    result = []
    for cluster in sorted(clusters, key=lambda item: item["count"], reverse=True)[:limit]:
        representative = cluster["raw_counter"].most_common(1)[0][0]
        keywords = [item["keyword"] for item in extract_hot_keywords(cluster["examples"], 5)]
        result.append({
            "question": cluster["semantic_label"] or representative,
            "semantic_label": cluster["semantic_label"],
            "representative_question": representative,
            "count": cluster["count"],
            "examples": cluster["examples"],
            "keywords": keywords,
        })
    return result
