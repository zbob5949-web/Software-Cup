# -*- coding: utf-8 -*-
# ==================== 接口25：语音转文字 ====================
#这段代码实现了一个语音转文字（ASR）接口，使用 OpenAI 的 Whisper 模型将上传的音频文件转换为文字。
# 上传音频文件，返回识别文字
# 前端调用：FormData 上传 file 字段 + language 参数
# 前端接收：{code, msg, data: {text, language}}
import whisper
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Query
from utils.response import Result
from core.config import MAX_AUDIO_UPLOAD_BYTES

router = APIRouter()

ASR_MODEL_NAME = "small"
_whisper_model = None
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".webm"}
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/ogg", "audio/webm",
}

def _get_model():
    global _whisper_model
    if _whisper_model is None:
        print("[ASR] 正在加载 Whisper 模型...")
        _whisper_model = whisper.load_model(ASR_MODEL_NAME)
        print("[ASR] Whisper 模型加载完成")
    return _whisper_model

@router.post("/api/asr/transcribe")
async def asr_transcribe(
    file: UploadFile = File(...),
    language: str = Query("zh", description="zh=中文, en=英文, auto=自动检测")
):
    if not file:
        return Result(400, "请上传音频文件")

    if file.content_type not in ALLOWED_AUDIO_TYPES:
        return Result(400, f"不支持的音频类型: {file.content_type}")

    tmp_path = None
    try:
        content = await file.read(MAX_AUDIO_UPLOAD_BYTES + 1)
        if not content:
            return Result(400, "音频文件为空")
        if len(content) > MAX_AUDIO_UPLOAD_BYTES:
            return Result(413, "音频文件过大")

        suffix = os.path.splitext(file.filename or "")[1].lower() or ".wav"
        if suffix not in ALLOWED_AUDIO_EXTENSIONS:
            return Result(400, "不支持的音频文件后缀")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        model = _get_model()
        options = {"fp16": False}
        if language != "auto":
            options["language"] = language

        print(f"[ASR] 开始识别: {file.filename}")
        result = model.transcribe(tmp_path, **options)
        text = result["text"].strip()

        return Result(200, "识别成功", {
            "text": text,
            "language": result.get("language", language)
        })
    except Exception as e:
        print(f"[ASR] 识别失败: {e}")
        return Result(500, "识别失败，请稍后再试")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

@router.get("/api/asr/health")
def health():
    return Result(200, "success", {"model_loaded": _whisper_model is not None})
