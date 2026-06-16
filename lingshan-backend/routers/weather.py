# ==================== 接口26：景区天气 ====================
# 前端：GET /api/weather
# 返回：{code, msg, data: {city, temperature, weather, icon, advice}}
# 数据源：和风天气API（未配置Key时返回兜底数据）
import httpx
import os
from fastapi import APIRouter
from utils.response import Result

router = APIRouter()

HEFENG_API_KEY = os.getenv("HEFENG_API_KEY")
API_HOST = "ne6fr8qduc.re.qweatherapi.com"
LOCATION = "101190204"  # 无锡灵山

@router.get("/api/weather")
async def get_weather():
    if not HEFENG_API_KEY:
        print("[天气] 未配置 HEFENG_API_KEY，使用兜底数据")
        return Result(200, "success", {
            "city": "无锡灵山", "temperature": "26°C", "weather": "晴",
            "icon": "100", "advice": "天气数据加载中，请稍后刷新"
        })

    async with httpx.AsyncClient() as client:
        try:
            weather_url = f"https://{API_HOST}/v7/weather/now?location={LOCATION}&key={HEFENG_API_KEY}"
            index_url = f"https://{API_HOST}/v7/indices/1d?location={LOCATION}&key={HEFENG_API_KEY}&type=0"

            weather_resp = await client.get(weather_url, timeout=10.0)
            weather_data = weather_resp.json()

            index_resp = await client.get(index_url, timeout=10.0)
            index_data = index_resp.json()

            if weather_data.get("code") != "200":
                raise Exception(f"天气API错误: {weather_data.get('code')}")
            if index_data.get("code") != "200":
                raise Exception(f"指数API错误: {index_data.get('code')}")

            now = weather_data["now"]
            temp, text, icon = now["temp"], now["text"], now["icon"]

            advice_list = index_data.get("daily", [])
            umbrella_advice = ""
            uv_advice = ""
            for item in advice_list:
                if item["name"] == "紫外线指数":
                    uv_advice = item["category"]
                    if uv_advice in ["中", "强", "很强"]:
                        umbrella_advice = "建议涂抹防晒霜或打遮阳伞"
                elif item["name"] == "雨伞指数":
                    if "建议" in item["category"] and "雨" in item["category"]:
                        umbrella_advice = item["category"]
            if not umbrella_advice:
                umbrella_advice = "天气适宜，祝您游玩愉快"

            return Result(200, "success", {
                "city": "无锡灵山",
                "temperature": f"{temp}°C",
                "weather": text,
                "icon": icon,
                "advice": f"紫外线{uv_advice}，{umbrella_advice}"
            })
        except Exception as e:
            print(f"[天气] 获取失败: {e}")
            return Result(200, "success", {
                "city": "无锡灵山", "temperature": "26°C", "weather": "晴",
                "icon": "100", "advice": "数据加载中，请稍后刷新"
            })
