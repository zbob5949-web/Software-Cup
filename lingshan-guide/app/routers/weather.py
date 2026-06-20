import httpx
from fastapi import HTTPException, FastAPI
import os
from fastapi import APIRouter

HEFENG_API_KEY = os.getenv("HEFENG_API_KEY")
API_HOST = "ne6fr8qduc.re.qweatherapi.com"  # 专属 Host (不带 https://)
LOCATION = "101190204"  # 无锡灵山 (和风天气 Location ID)

# --- 2. 应用初始化 ---
router=APIRouter()


@router.get("/api/weather")
async def get_weather():
    # --- 3. 调试：检查环境变量 ---
    if not HEFENG_API_KEY:
        print("❌ 错误：未找到环境变量 HEFENG_API_KEY")
        return {"error": "Server config error", "city": "无锡灵山", "temperature": "--", "weather": "未知",
                "advice": "请检查服务器配置"}

    async with httpx.AsyncClient() as client:
        try:
            # --- 4. 拼接 URL ---
            # 注意：这里手动拼接 https://，因为 API_HOST 只存域名
            weather_url = f"https://{API_HOST}/v7/weather/now?location={LOCATION}&key={HEFENG_API_KEY}"
            index_url = f"https://{API_HOST}/v7/indices/1d?location={LOCATION}&key={HEFENG_API_KEY}&type=0"

            # --- 5. 调试：打印将要请求的地址 ---
            print(f"\n--- 调试信息 ---")
            print(f"正在请求天气: {weather_url}")
            print(f"正在请求指数: {index_url}")

            # --- 6. 发送请求 ---
            weather_resp = await client.get(weather_url, timeout=10.0)
            weather_data = weather_resp.json()
            print(f"【天气API】返回状态码: {weather_resp.status_code}")
            #print(f"【天气API】返回内容: {weather_data}")

            index_resp = await client.get(index_url, timeout=10.0)
            index_data = index_resp.json()
            print(f"【指数API】返回状态码: {index_resp.status_code}")
            #print(f"【指数API】返回内容: {index_data}")

            # --- 7. 检查返回码 ---
            if weather_data.get("code") != "200":
                raise HTTPException(status_code=400, detail=f"天气API错误: {weather_data.get('code')}")

            if index_data.get("code") != "200":
                raise HTTPException(status_code=400, detail=f"指数API错误: {index_data.get('code')}")

            # --- 8. 数据清洗 ---
            now = weather_data["now"]
            temp = now["temp"]
            text = now["text"]
            icon = now["icon"]

            # --- 9. 建议逻辑 ---
            advice_list = index_data.get("daily", [])
            umbrella_advice = ""
            uv_advice = ""
            dress_advice = ""

            for item in advice_list:
                if item["name"] == "紫外线指数":
                    uv_advice = item["category"]
                    if uv_advice in ["中", "强", "很强"]:
                        umbrella_advice = "建议涂抹防晒霜或打遮阳伞"
                elif item["name"] == "穿衣指数":
                    dress_advice = item["category"]
                elif item["name"] == "雨伞指数":
                    if "建议" in item["category"] and "雨" in item["category"]:
                        umbrella_advice = item["category"]

            if not umbrella_advice:
                umbrella_advice = "天气适宜，祝您游玩愉快"

            # --- 10. 返回数据 ---
            return {
                "city": "无锡灵山",
                "temperature": f"{temp}°C",
                "weather": text,
                "icon": icon,
                "advice": f"紫外线{uv_advice}，{umbrella_advice}"
            }

        except Exception as e:
            # --- 11. 异常处理 ---
            print(f"❌ 发生异常: {e}")

            # 返回兜底数据，防止前端崩溃
            return {
                "city": "无锡灵山",
                "temperature": "26°C",
                "weather": "晴",
                "icon": "100",
                "advice": "数据加载中，请稍后刷新"
            }

