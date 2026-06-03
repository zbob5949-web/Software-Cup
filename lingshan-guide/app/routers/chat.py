import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import get_db, get_current_user_optional, get_current_user
from app.utils.response import Result
from app.services import chat_service

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    session_id: str = None   # 可不传，自动生成

class DetailRequest(BaseModel):
    session_id: str


# ---------- AI 对话 ----------
@router.post("/api/user/chat")
def chat(
    req: ChatRequest,
    phone: str = Depends(get_current_user_optional),
    db=Depends(get_db)
):
    """用户发送消息，返回智能回复"""
    question = req.question.strip()
    if not question:
        return Result(400, "问题不能为空")

    session_id = req.session_id or uuid.uuid4().hex

    try:
        cursor = db.cursor()
        # 1. 保存用户消息
        chat_service.save_message(cursor, session_id, phone, "user", question)

        # 2. 处理并获取回复
        result = chat_service.process_user_chat(cursor, question, session_id, phone)
        reply = result["reply"]
        source = result["source"]

        # 3. 保存机器人回复
        chat_service.save_message(cursor, session_id, phone, "assistant", reply)

        # 4. 清理会话旧记录
        chat_service.cleanup_old_records(cursor, session_id)

        db.commit()
        return Result(200, "success", {
            "reply": reply,
            "source": source,
            "session_id": session_id
        })
    except Exception as e:
        db.rollback()
        return Result(500, f"处理失败：{str(e)}")


# ---------- 历史会话列表 ----------
@router.get("/api/user/history")
def history(phone: str = Depends(get_current_user), db=Depends(get_db)):
    """已登录用户的历史会话列表"""
    cursor = db.cursor()
    sessions = chat_service.get_user_sessions(cursor, phone)
    return Result(200, "success", sessions)


# ---------- 会话详情 ----------
@router.get("/api/user/chat/detail")
def chat_detail(session_id: str, phone: str = Depends(get_current_user), db=Depends(get_db)):
    """查看指定会话的所有消息"""
    cursor = db.cursor()
    messages = chat_service.get_session_messages(cursor, session_id, phone)
    if not messages:
        return Result(404, "会话不存在")
    return Result(200, "success", messages)