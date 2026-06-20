import os
from datetime import datetime
import requests


HEFENG_API_KEY = os.getenv("HEFENG_API_KEY")
API_HOST = os.getenv("HEFENG_API_HOST", "ne6fr8qduc.re.qweatherapi.com")
LOCATION = os.getenv("HEFENG_LOCATION", "101190204")
CITY_NAME = "无锡灵山"

WEATHER_WORDS = {
    "天气", "气温", "温度", "多少度", "几度", "冷吗", "热吗", "冷不冷", "热不热",
    "下雨", "有雨", "雨", "带伞", "伞", "防晒", "紫外线", "风大", "刮风",
    "适合游玩", "适合去", "适不适合", "穿什么", "穿衣",
}

WEATHER_TIME_WORDS = {"今天", "今日", "现在", "当前", "实时", "明天", "明日", "后天"}
OUTDOOR_INTENT_WORDS = {
    "适合玩吗", "适合游玩吗", "适合去吗", "能去玩吗", "好玩吗",
    "要带伞吗", "需要带伞吗", "会下雨吗", "会不会下雨",
    "冷不冷", "热不热", "穿什么", "怎么穿",
}


def is_weather_query(query: str) -> bool:
    q = (query or "").strip()
    if not q:
        return False
    if any(word in q for word in WEATHER_WORDS):
        return True
    return any(time_word in q for time_word in WEATHER_TIME_WORDS) and any(
        intent_word in q for intent_word in OUTDOOR_INTENT_WORDS
    )


def get_weather_data() -> dict:
    if not HEFENG_API_KEY:
        return {
            "error": "Server config error",
            "city": CITY_NAME,
            "temperature": "--",
            "weather": "未知",
            "advice": "请检查服务器配置",
        }

    try:
        weather_url = f"https://{API_HOST}/v7/weather/now"
        index_url = f"https://{API_HOST}/v7/indices/1d"
        params = {"location": LOCATION, "key": HEFENG_API_KEY}

        weather_resp = requests.get(weather_url, params=params, timeout=10)
        weather_data = weather_resp.json()
        index_resp = requests.get(index_url, params={**params, "type": 0}, timeout=10)
        index_data = index_resp.json()

        if weather_data.get("code") != "200":
            raise RuntimeError(f"天气API错误: {weather_data.get('code')}")
        if index_data.get("code") != "200":
            raise RuntimeError(f"指数API错误: {index_data.get('code')}")

        now = weather_data["now"]
        advice = build_weather_advice(index_data.get("daily", []))
        return {
            "city": CITY_NAME,
            "temperature": f"{now['temp']}°C",
            "weather": now["text"],
            "icon": now["icon"],
            "advice": advice,
            "updated_at": now.get("obsTime") or datetime.now().isoformat(timespec="seconds"),
        }
    except Exception:
        return {
            "city": CITY_NAME,
            "temperature": "26°C",
            "weather": "晴",
            "icon": "100",
            "advice": "数据加载中，请稍后刷新",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }


def build_weather_advice(daily: list) -> str:
    umbrella_advice = ""
    uv_advice = ""
    dress_advice = ""

    for item in daily:
        name = item.get("name", "")
        category = item.get("category", "")
        if name == "紫外线指数":
            uv_advice = category
            if uv_advice in {"中", "强", "很强"}:
                umbrella_advice = "建议涂抹防晒霜或打遮阳伞"
        elif name == "穿衣指数":
            dress_advice = category
        elif name == "雨伞指数" and "建议" in category and "雨" in category:
            umbrella_advice = category

    if not umbrella_advice:
        umbrella_advice = "天气适宜，祝您游玩愉快"

    parts = []
    if uv_advice:
        parts.append(f"紫外线{uv_advice}")
    if dress_advice:
        parts.append(f"穿衣指数{dress_advice}")
    parts.append(umbrella_advice)
    return "，".join(parts)


def format_weather_reply(data: dict) -> str:
    error = data.get("error")
    if error:
        return (
            f"{data.get('city', CITY_NAME)}天气服务暂时不可用，"
            f"{data.get('advice', '请稍后再试')}。"
        )
    return (
        f"{data.get('city', CITY_NAME)}当前天气："
        f"{data.get('weather', '未知')}，"
        f"{data.get('temperature', '--')}。"
        f"{data.get('advice', '')}"
    ).strip()
