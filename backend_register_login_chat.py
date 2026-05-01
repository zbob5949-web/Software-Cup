from fastapi import FastAPI
from pydantic import BaseModel
import os
from openai import OpenAI
from fastapi.middleware.cors import CORSMiddleware

# 模拟数据库：用于存储用户信息
# 注意：这是内存数据，后端重启后，新注册的用户会消失
userDb = [
    {"username": "test01", "password": "123456"},
    {"username": "admin", "password": "admin123"},
    {"username": "user001", "password": "666888"}
]

# 记录登录状态
loginStatus = {
    "is_login": False,
    "username": "",
}

# 记录聊天历史
chatHistory = []

systemPrompt = (
    "你是苏州灵山景区导览数字人，名字叫灵小导。"
    "请用简洁、亲切、准确的语言回答游客关于景区开放时间、景点介绍、路线推荐、"
    "门票预约、交通方式和游玩注意事项等问题。"
)

app = FastAPI(title="灵山景区导览数字人", version="1.10")

# CORS 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册表单
class RegisterForm(BaseModel):
    username: str
    password: str


# 登录表单
class LoginForm(BaseModel):
    username: str
    password: str


# AI 聊天表单
class ChatForm(BaseModel):
    question: str


# 首页测试接口
@app.get("/")
async def Home():
    return {
        "code": 200,
        "msg": "灵山景区导览数字人后端服务已启动",
        "data": None
    }


# 注册接口
@app.post("/register")
async def RegisterUser(form: RegisterForm):
    username = form.username.strip()
    password = form.password

    if not username:
        return {
            "code": 40001,
            "msg": "请输入用户名",
            "data": None
        }

    if not password:
        return {
            "code": 40002,
            "msg": "请输入密码",
            "data": None
        }

    # 判断用户名是否已存在
    for user in userDb:
        if user["username"] == username:
            return {
                "code": 40901,
                "msg": "用户名已存在",
                "data": None
            }

    # 将新用户加入模拟数据库
    userDb.append({
        "username": username,
        "password": password
    })

    return {
        "code": 200,
        "msg": "注册成功",
        "data": {
            "username": username
        }
    }


# 登录接口
@app.post("/login")
async def LoginUser(form: LoginForm):
    global loginStatus

    username = form.username.strip()
    password = form.password

    if not username:
        return {
            "code": 40001,
            "msg": "请输入用户名",
            "data": None
        }

    if not password:
        return {
            "code": 40002,
            "msg": "请输入密码",
            "data": None
        }

    for user in userDb:
        if user["username"] == username and user["password"] == password:
            loginStatus["is_login"] = True
            loginStatus["username"] = username
            return {
                "code": 200,
                "msg": "登录成功",
                "data": {
                    "username": username
                }
            }

    return {
        "code": 40101,
        "msg": "账号或密码错误",
        "data": None
    }


# 退出登录接口
@app.post("/logout")
async def LogoutUser():
    global loginStatus

    loginStatus["is_login"] = False
    loginStatus["username"] = ""

    return {
        "code": 200,
        "msg": "退出成功",
        "data": None
    }


# AI 聊天接口
@app.post("/chat")
async def ChatWithAi(form: ChatForm):
    if not loginStatus["is_login"]:
        return {
            "code": 40100,
            "msg": "请先登录",
            "data": None
        }

    question = form.question.strip()

    if not question:
        return {
            "code": 40404,
            "msg": "问题不能为空",
            "data": None
        }

    apiKey = os.environ.get("OPENAI_API_KEY")

    if not apiKey:
        return {
            "code": 50001,
            "msg": "未配置 DeepSeek API Key，请先设置 OPENAI_API_KEY 环境变量",
            "data": None
        }

    try:
        client = OpenAI(
            api_key=apiKey,
            base_url="https://api.deepseek.com"
        )

        messages = [{"role": "system", "content": systemPrompt}]
        messages += chatHistory
        messages.append({"role": "user", "content": question})

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )

        answer = response.choices[0].message.content

        # 保存对话历史
        chatHistory.append({"role": "user", "content": question})
        chatHistory.append({"role": "assistant", "content": answer})

        return {
            "code": 200,
            "msg": "success",
            "data": {
                "question": question,
                "answer": answer
            }
        }

    except Exception as e:
        return {
            "code": 50000,
            "msg": f"AI服务异常：{str(e)}",
            "data": None
        }
