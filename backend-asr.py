# -*- coding: utf-8 -*-
"""
ASR 语音识别服务 (独立版)
功能：将上传的音频文件转写为文本
依赖库：fastapi, uvicorn, whisper, python-multipart
启动命令：uvicorn asr_server:app --host 0.0.0.0 --port 8001
"""

from fastapi import FastAPI, UploadFile, File, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
import whisper
import tempfile
import os
import asyncio

# ====================== 配置区 ======================
# Whisper 模型配置 (可选: tiny, base, small, medium, large)
# 推荐使用 small 或 base，兼顾速度与准确率
ASR_MODEL_NAME = "small"

# ====================== 全局变量 ======================
app = FastAPI(title="灵山景区 ASR 服务", version="1.0")

# 全局模型变量 (用于懒加载)
whisper_model = None


# ====================== 工具函数 ======================
def get_whisper_model():
    """懒加载 Whisper 模型"""
    global whisper_model
    if whisper_model is None:
        print("[ASR] 正在加载 Whisper 模型...")
        whisper_model = whisper.load_model(ASR_MODEL_NAME)
        print(f"[ASR] Whisper 模型 ({ASR_MODEL_NAME}) 加载完成")
    return whisper_model


# ====================== 核心接口 ======================
@app.post("/api/asr/transcribe")
async def asr_transcribe(
        file: UploadFile = File(...),
        language: str = Query("zh", description="语言代码: zh=中文, en=英文, auto=自动检测")
):
    """
    ASR 语音识别接口。
    支持格式：wav, mp3, m4a, ogg, webm
    """
    if not file:
        return JSONResponse({"code": 40004, "msg": "请上传音频文件"})

    # 验证文件类型
    allowed_types = [
        "audio/wav", "audio/mpeg", "audio/mp3", "audio/mp4",
        "audio/m4a", "audio/ogg", "audio/webm", "audio/x-wav"
    ]
    if file.content_type not in allowed_types:
        return JSONResponse({"code": 40001, "msg": f"不支持的音频类型: {file.content_type}"})

    temp_path = None
    try:
        # 读取上传的音频
        content = await file.read()
        if len(content) == 0:
            return JSONResponse({"code": 40002, "msg": "音频文件为空"})

        # 创建临时文件
        suffix = os.path.splitext(file.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        # 加载模型并识别
        model = get_whisper_model()
        options = {"fp16": False}  # CPU模式需关闭fp16
        if language != "auto":
            options["language"] = language

        print(f"[ASR] 开始识别: {file.filename}")
        result = model.transcribe(temp_path, **options)
        recognized_text = result["text"].strip()

        return JSONResponse({
            "code": 200,
            "msg": "识别成功",
            "data": {
                "text": recognized_text,
                "language": result.get("language", language)
            }
        })

    except Exception as e:
        print(f"[ASR] 识别失败: {e}")
        return JSONResponse({"code": 50002, "msg": f"识别失败: {str(e)}"})

    finally:
        # 清理临时文件
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception as e:
                print(f"[ASR] 清理临时文件失败: {e}")


# 健康检查接口
@app.get("/health")
def health_check():
    return {"status": "ASR Service Running", "model_loaded": whisper_model is not None}


if __name__ == "__main__":
    import uvicorn

    # 注意：独立运行时请指定一个未被占用的端口，例如 8001
    uvicorn.run(app, host="0.0.0.0", port=8001)