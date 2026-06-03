import os
import uuid
from datetime import datetime
from fastapi import Request, Response
import pymysql


# 假设你已经有一个初始化好的 Chroma DB 实例
# 请确保在文件顶部或其他地方已经初始化了 vectorstore
# from your_db_module import vectorstore

@app.post("/api/user/chat")
async def chat(form: ChatForm, request: Request, response: Response):
    question = form.question.strip()
    if not question:
        return Result(40004, "请输入问题")

    # --- 1. 身份识别与 Cookie 处理 ---
    login_state = request.cookies.get("login_state")
    visitor_id = request.cookies.get("visitor_id")

    if login_state:
        current_user = login_state
    else:
        current_user = visitor_id or f"guest_{int(datetime.timestamp(datetime.now()))}"
        response.set_cookie(key="visitor_id", value=current_user, max_age=604800)

    # --- 2. 会话管理 ---
    if not form.session_id or form.session_id.lower() == "new":
        session_id = str(uuid.uuid4())
    else:
        session_id = form.session_id

    conn = get_db_connection()
    if not conn:
        return Result(50001, "数据库连接失败，请稍后重试")

    try:
        with conn.cursor() as cursor:
            # --- 3. 构建历史消息 (System + History) ---
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]

            cursor.execute("""
                SELECT role, content 
                FROM chat_records 
                WHERE username = %s AND session_id = %s 
                ORDER BY timestamp ASC
            """, (current_user, session_id))

            for role, content in cursor.fetchall():
                messages.append({"role": role, "content": content})

            # --- 4. RAG 检索增强 (核心改动) ---
            # a. 检索相关文档片段
            # 注意：这里假设你有一个全局的 vectorstore 实例
            # 如果没有，请先在脚本开头初始化：vectorstore = Chroma(...)
            retrieved_docs = vectorstore.similarity_search(question, k=4)  # 检索4个最相关的片段

            # b. 构建 RAG 上下文字符串
            context_parts = ["【参考知识库】"]
            for i, doc in enumerate(retrieved_docs):
                content = doc.page_content[:500]  # 截断防止过长
                source = doc.metadata.get("source", "未知来源")
                context_parts.append(f"片段 {i + 1} (来源: {source}):\n{content}\n")

            context_str = "\n".join(context_parts)

            # c. 将检索到的上下文注入到用户问题之前
            # 这样 SYSTEM_PROMPT 就能看到这些知识了
            final_user_message = f"{context_str}\n\n【当前用户问题】\n{question}"

            # --- 5. 调用 AI (DeepSeek) ---
            my_key = os.environ.get('DEEPSEEK_KEY')
            if not my_key:
                return Result(50003, "服务配置错误：未设置 DEEPSEEK_KEY 环境变量")

            client = OpenAI(api_key=my_key, base_url="https://api.deepseek.com")

            # 将构建好的包含上下文的消息发送给模型
            messages.append({"role": "user", "content": final_user_message})

            ai_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=False
            )
            answer = ai_response.choices[0].message.content

            # --- 6. 保存记录 (只保存原始问题，不保存注入的上下文，保持记录整洁) ---
            cursor.execute("""
                INSERT INTO chat_records (username, session_id, role, content) 
                VALUES (%s, %s, %s, %s)
            """, (current_user, session_id, "user", question))

            cursor.execute("""
                INSERT INTO chat_records (username, session_id, role, content) 
                VALUES (%s, %s, %s, %s)
            """, (current_user, session_id, "assistant", answer))

            # --- 7. 清理旧记录 ---
            cursor.execute("""
                DELETE FROM chat_records 
                WHERE username = %s AND session_id = %s AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM chat_records 
                        WHERE username = %s AND session_id = %s 
                        ORDER BY timestamp DESC LIMIT 10
                    ) AS tmp
                )
            """, (current_user, session_id, current_user, session_id))

            conn.commit()
            return Result(200, "success", {"answer": answer, "session_id": session_id})

    except Exception as e:
        conn.rollback()
        print(f"[chat 错误] {e}")
        return Result(50002, "AI 处理失败，请稍后重试")
    finally:
        conn.close()