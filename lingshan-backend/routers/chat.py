# ==================== 对话模块 ====================
# 接口11-15：文字对话 / 语音对话 / 音频下载 / 历史列表 / 会话详情
import uuid
import os
import re
import tempfile
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dependencies import get_db, get_current_user_optional, get_current_user
from core.config import MAX_AUDIO_UPLOAD_BYTES, MAX_CHAT_QUESTION_LENGTH
from utils.response import Result
from services import chat_service

router = APIRouter()

# 语音模型懒加载（首次调用慢，后续快）
_whisper_model = None
AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "audio_output")
ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".webm"}
ALLOWED_AUDIO_TYPES = {
    "audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/ogg", "audio/webm",
}


def _valid_session_id(session_id: Optional[str]) -> bool:
    return not session_id or bool(re.fullmatch(r"[A-Za-z0-9_-]{16,64}", session_id))

def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        print("[Chat] 正在加载 Whisper 模型...")
        _whisper_model = whisper.load_model("small")
        print("[Chat] Whisper 模型加载完成")
    return _whisper_model


def _get_active_voice(cursor) -> str:
    """语音对话回复优先使用管理后台启用的数字人声音。"""
    try:
        cursor.execute(
            "SELECT voice_name FROM digital_human_configs "
            "WHERE is_active = TRUE ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        if row and row.get("voice_name"):
            return row["voice_name"]
    except Exception:
        pass
    return "zh-CN-XiaoxiaoNeural"

# ----- 请求模型 -----
class ChatRequest(BaseModel):
    question: str = Field(..., max_length=MAX_CHAT_QUESTION_LENGTH)  # 用户问题（必填）
    session_id: Optional[str] = Field(None, max_length=64)            # 会话ID（不传则自动创建新会话）

# ===== 接口11：AI文字对话 =====
# 说明：首次调用不传session_id会自动创建，后续传同一个session_id维持上下文
@router.post("/api/user/chat", include_in_schema=False)  # 旧路径兼容
@router.post("/api/chat")
def chat(
    req: ChatRequest,
    phone: str = Depends(get_current_user_optional),
    db=Depends(get_db)
):
    question = req.question.strip()
    if not question:
        return Result(400, "问题不能为空")
    if not _valid_session_id(req.session_id):
        return Result(400, "会话ID格式不正确")

    session_id = req.session_id or uuid.uuid4().hex

    try:
        with db.cursor() as cursor:
            chat_service.save_message(cursor, session_id, phone, "user", question)
            result = chat_service.process_user_chat(cursor, question, session_id, phone)
            reply = result["reply"]
            source = result["source"]
            chat_service.save_message(cursor, session_id, phone, "assistant", reply, source)
            chat_service.cleanup_old_records(cursor, session_id, phone)
        db.commit()
        digital_human = chat_service.infer_digital_human_directives(question, reply, source)
        return Result(200, "success", {
            "reply": reply,
            "source": source,       # faq/dify/ai/local/spot/route/service/fallback
            "session_id": session_id,
            "digital_human": digital_human
        })
    except Exception as e:
        db.rollback()
        print(f"[chat 错误] {e}")
        return Result(500, "处理失败，请稍后再试")

# ===== 接口12：一站式语音对话 =====
# 流程：上传音频 → ASR识别 → AI对话 → TTS合成 → 返回文字+音频URL
# 注意：首次调用Whisper加载约需10-30秒，之后快
@router.post("/api/chat/voice")
async def voice_chat(
    audio: UploadFile = File(...),
    session_id: str = None,
    phone: str = Depends(get_current_user_optional),
    db=Depends(get_db)
):
    tmp_in_path = None
    try:
        if session_id and not _valid_session_id(session_id):
            return Result(400, "会话ID格式不正确")
        if audio.content_type not in ALLOWED_AUDIO_TYPES:
            return Result(400, f"不支持的音频类型: {audio.content_type}")
        # 1. 保存上传音频
        suffix = os.path.splitext(audio.filename or "audio.wav")[1] or ".wav"
        suffix = suffix.lower()
        if suffix not in ALLOWED_AUDIO_EXTENSIONS:
            return Result(400, "不支持的音频文件后缀")
        tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp_in_path = tmp_in.name
        content = await audio.read(MAX_AUDIO_UPLOAD_BYTES + 1)
        if not content:
            return Result(400, "音频文件为空")
        if len(content) > MAX_AUDIO_UPLOAD_BYTES:
            return Result(413, "音频文件过大")
        tmp_in.write(content)
        tmp_in.close()

        # 2. ASR识别
        model = _get_whisper_model()
        result_asr = model.transcribe(tmp_in_path, fp16=False, language="zh")
        question = result_asr["text"].strip()
        if not question:
            return Result(400, "未能识别到语音内容")

        # 3. AI对话
        session_id = session_id or uuid.uuid4().hex
        with db.cursor() as cursor:
            chat_service.save_message(cursor, session_id, phone, "user", question)
            result_chat = chat_service.process_user_chat(cursor, question, session_id, phone)
            reply = result_chat["reply"]
            source = result_chat["source"]
            chat_service.save_message(cursor, session_id, phone, "assistant", reply, source)
            chat_service.cleanup_old_records(cursor, session_id, phone)
            voice_name = _get_active_voice(cursor)
        db.commit()

        # 4. TTS合成
        import edge_tts
        os.makedirs(AUDIO_DIR, exist_ok=True)
        audio_filename = f"{uuid.uuid4().hex}.mp3"
        audio_path = os.path.join(AUDIO_DIR, audio_filename)
        communicate = edge_tts.Communicate(
            text=reply[:500], voice=voice_name,
            rate="+10%", pitch="+0Hz"
        )
        await communicate.save(audio_path)
        digital_human = chat_service.infer_digital_human_directives(question, reply, source)
        digital_human["voice_name"] = voice_name

        return Result(200, "success", {
            "text": reply,
            "source": source,
            "session_id": session_id,
            "recognized_text": question,
            "audio_url": f"/api/chat/audio/{audio_filename}",
            "digital_human": digital_human
        })
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        print(f"[voice_chat 错误] {e}")
        return Result(500, "语音处理失败，请稍后再试")
    finally:
        if tmp_in_path and os.path.exists(tmp_in_path):
            try:
                os.unlink(tmp_in_path)
            except Exception:
                pass

# ===== 接口13：下载语音回复音频 =====
# 前端：GET /api/chat/audio/{filename}  →  直接播放或下载MP3
# 前端用法：<audio src="/api/chat/audio/abc123.mp3" controls></audio>
@router.get("/api/chat/audio/{filename}")
def get_audio(filename: str):
    if not re.fullmatch(r"[a-f0-9]{32}\.mp3", filename):
        raise HTTPException(status_code=400, detail="非法文件名")
    audio_root = os.path.abspath(AUDIO_DIR)
    path = os.path.abspath(os.path.join(audio_root, filename))
    if not path.startswith(audio_root + os.sep):
        raise HTTPException(status_code=400, detail="非法文件名")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="音频文件不存在或已过期")
    return FileResponse(path, media_type="audio/mpeg")

# ===== 接口14：历史会话列表 =====
# 旧路径 /api/user/history 保留兼容
@router.get("/api/user/history", include_in_schema=False)
@router.get("/api/chat/history")
def history(phone: str = Depends(get_current_user), db=Depends(get_db)):
    with db.cursor() as cursor:
        sessions = chat_service.get_user_sessions(cursor, phone)
    return Result(200, "success", sessions)

# ===== 接口15：会话消息详情 =====
# role: "user"=用户消息 / "assistant"=AI回复
# 旧路径 /api/user/chat/detail/{session_id} 保留兼容
@router.get("/api/user/chat/detail/{session_id}", include_in_schema=False)
@router.get("/api/chat/detail/{session_id}")
def chat_detail(session_id: str, phone: str = Depends(get_current_user), db=Depends(get_db)):
    if not _valid_session_id(session_id):
        return Result(400, "会话ID格式不正确")
    with db.cursor() as cursor:
        messages = chat_service.get_session_messages(cursor, session_id, phone)
    if not messages:
        return Result(404, "会话不存在")
    return Result(200, "success", messages)

# 保留旧接口兼容（query参数方式，已废弃）
@router.get("/api/user/chat/detail")
def chat_detail_legacy(session_id: str, phone: str = Depends(get_current_user), db=Depends(get_db)):
    return chat_detail(session_id, phone, db)
