# ==================== 导入模块 ====================
import os
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import edge_tts

# ==================== 初始化（如已有app可跳过） ====================
from fastapi import APIRouter
router = APIRouter()

# ==================== 配置参数 ====================
TTS_VOICE = "zh-CN-XiaoxiaoNeural"  # 中文女声，温柔清晰
TTS_RATE  = "+10%"                    # 语速，-50% ~ +100%
TTS_PITCH = "+0Hz"                   # 音调

# ==================== 数据模型 ====================
class TTSForm(BaseModel):
    text: str

# ==================== 文本转语音接口 ====================
@router.post("/api/tts")
async def text_to_speech(form: TTSForm):
    """
    接收文本，返回 MP3 音频流。
    前端可用 <audio> 或 fetch 后播放。
    文本长度超过 500 字会自动截断，避免生成超长音频。
    """
    text = form.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    # 限制长度（可根据需求调整）
    if len(text) > 500:
        text = text[:500]

    try:
        # 创建 TTS 通信实例
        communicate = edge_tts.Communicate(
            text=text,
            voice=TTS_VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
        )

        # 生成 MP3 并保存到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp_path = tmp.name
            await communicate.save(tmp_path)

        # 流式返回音频（读完文件后自动删除临时文件）
        def iterfile():
            with open(tmp_path, "rb") as f:
                yield from f
            os.unlink(tmp_path)  # 删除临时文件

        return StreamingResponse(
            iterfile(),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )

    except Exception as e:
        # 可替换为自定义日志记录
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")


