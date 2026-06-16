# ==================== 接口24：文本转语音 ====================
#这段代码实现了一个文本转语音（TTS）接口，使用微软 Edge TTS 服务将文字合成为 MP3 音频。
# 接收文字，返回 MP3 音频流
# 前端调用：fetch POST /api/tts  body: {text: "要合成的文字"}
# 前端接收：audio/mpeg 二进制流，用 <audio> 或 URL.createObjectURL 播放
import os
import tempfile
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import edge_tts
from dependencies import get_db
from utils.response import Result

router = APIRouter()

TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 中文女声，温柔清晰
TTS_RATE  = "+10%"                   # 语速
TTS_PITCH = "+0Hz"                   # 音调

class TTSForm(BaseModel):
    text: str = Field(..., max_length=500)
    voice_name: str | None = Field(None, max_length=100)


def _get_active_voice(db) -> str:
    """优先使用管理后台启用的数字人声音配置。"""
    try:
        with db.cursor() as cursor:
            cursor.execute(
                "SELECT voice_name FROM digital_human_configs "
                "WHERE is_active = TRUE ORDER BY id DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row and row.get("voice_name"):
                return row["voice_name"]
    except Exception:
        pass
    return TTS_VOICE

@router.post("/api/tts")
async def text_to_speech(form: TTSForm, db=Depends(get_db)):
    text = form.text.strip()
    if not text:
        return Result(400, "文本不能为空")

    try:
        voice = form.voice_name or _get_active_voice(db)
        communicate = edge_tts.Communicate(
            text=text, voice=voice, rate=TTS_RATE, pitch=TTS_PITCH
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
            await communicate.save(tmp_path)

        def iterfile():
            with open(tmp_path, "rb") as f:
                yield from f
            os.unlink(tmp_path)

        return StreamingResponse(
            iterfile(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
    except Exception as e:
        print(f"[TTS 错误] {e}")
        return Result(500, "语音合成失败，请稍后再试")
