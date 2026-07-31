# -*- coding: utf-8 -*-
"""
ASR 语音识别服务
功能：将上传的音频文件转写为文本
启动命令：uvicorn asr_server:app --host 0.0.0.0 --port 8001

核心流程：
  浏览器录音 (webm/opus) → 上传 → ffmpeg 转标准 WAV → Whisper 识别 → 返回文本
  用 ffmpeg 做格式转换是最可靠的方案，避免 Whisper/torchaudio 在不同平台
  解码 webm/opus 时出现兼容性问题。
"""

from fastapi import FastAPI, UploadFile, File, Query, Depends, HTTPException
from fastapi.responses import JSONResponse
import whisper
import tempfile
import os
import subprocess
import asyncio

# ====================== 配置区 ======================
# 先 small 快速验证，确认管道正常后改 medium（中文准确率更高）
ASR_MODEL_NAME = "small"

# ====================== 全局变量 ======================
from fastapi import APIRouter
router = APIRouter()

whisper_model = None


def get_whisper_model():
    """懒加载 Whisper 模型"""
    global whisper_model
    if whisper_model is None:
        print(f"[ASR] 正在加载 Whisper 模型 ({ASR_MODEL_NAME})...")
        whisper_model = whisper.load_model(ASR_MODEL_NAME)
        print(f"[ASR] Whisper 模型 ({ASR_MODEL_NAME}) 加载完成")
    return whisper_model


def convert_to_wav(src_path: str) -> str:
    """
    用 ffmpeg 将任意音频转为 16kHz 单声道 WAV。
    Whisper 对这种格式的兼容性最好，跨平台也不会有解码问题。
    返回转换后的 .wav 文件路径。
    """
    # 输出到同名 .wav（临时文件旁边）
    wav_path = src_path + ".converted.wav"
    cmd = [
        "ffmpeg", "-y",                      # -y 覆盖已有文件
        "-i", src_path,                      # 输入
        "-ar", "16000",                      # 采样率 16kHz
        "-ac", "1",                          # 单声道
        "-sample_fmt", "s16",                # 16-bit PCM
        "-f", "wav",                         # WAV 容器
        "-loglevel", "error",                # 只输出错误
        wav_path,
    ]
    try:
        subprocess.run(cmd, check=True, timeout=15)
        return wav_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg 音频转换失败（返回码 {e.returncode}），请确认音频文件未损坏")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg 转换超时，音频文件可能过大")


# ====================== 核心接口 ======================
@router.post("/api/asr/transcribe")
async def asr_transcribe(
        file: UploadFile = File(...),
        language: str = Query("zh", description="语言代码: zh=中文, en=英文, auto=自动检测")
):
    """
    ASR 语音识别接口。
    浏览器将录音上传后，后端先通过 ffmpeg 转为标准 WAV，再交给 Whisper 识别。
    """
    if not file:
        return JSONResponse({"code": 40004, "msg": "请上传音频文件"})

    # 宽松的类型校验：只要不是明显非音频就放行（ffmpeg 会兜底）
    content_type = (file.content_type or "").split(";", 1)[0].lower()
    print(f"[ASR] 收到文件: {file.filename}, Content-Type={content_type or '未知'}")

    temp_path = None
    wav_path = None
    try:
        content = await file.read()
        if len(content) == 0:
            return JSONResponse({"code": 40002, "msg": "音频文件为空"})
        if len(content) < 512:
            return JSONResponse({"code": 40003, "msg": "音频太短，请录制至少 1 秒"})

        # 1. 保存上传的原始文件
        suffix = os.path.splitext(file.filename)[1] or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            temp_path = tmp.name

        print(f"[ASR] 原始音频已保存: {len(content)} bytes, 开始 ffmpeg 转码...")

        # 2. ffmpeg 转标准 WAV（16kHz / mono / 16bit PCM）
        wav_path = convert_to_wav(temp_path)
        wav_size = os.path.getsize(wav_path) if os.path.exists(wav_path) else 0
        print(f"[ASR] ffmpeg 转码完成, WAV 大小={wav_size} bytes")

        # 3. Whisper 识别
        model = get_whisper_model()
        options = {
            "fp16": False,
            "task": "transcribe",
            "temperature": 0.0,
            "compression_ratio_threshold": 2.4,
            "logprob_threshold": -1.0,
            "no_speech_threshold": 0.6,
        }
        if language != "auto":
            options["language"] = language

        print(f"[ASR] Whisper 开始识别...")
        result = model.transcribe(wav_path, **options)
        recognized_text = result["text"].strip()

        print(f"[ASR] 识别完成: '{recognized_text}' (语言={result.get('language', '?')})")
        return JSONResponse({
            "code": 200,
            "msg": "识别成功",
            "data": {
                "text": recognized_text,
                "language": result.get("language", language)
            }
        })

    except subprocess.CalledProcessError as e:
        print(f"[ASR] ffmpeg 失败: {e}")
        return JSONResponse({"code": 50003, "msg": "音频解码失败，请重试"})
    except Exception as e:
        print(f"[ASR] 识别异常: {type(e).__name__}: {e}")
        return JSONResponse({"code": 50002, "msg": f"识别失败: {str(e)}"})

    finally:
        # 清理临时文件
        for p in (temp_path, wav_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass


# 健康检查接口
@router.get("/health")
def health_check():
    return {"status": "ASR Service Running", "model": ASR_MODEL_NAME, "model_loaded": whisper_model is not None}
