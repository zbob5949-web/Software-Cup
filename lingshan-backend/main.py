from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from database import close_db_pool, init_database
from core.config import CORS_ORIGINS
from routers import user, spots, routes, feedback, favorites, faq, chat, tts, asr, weather, admin

@asynccontextmanager
#应用生命周期管理 (lifespan)
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库
    init_database()
    yield
    # 关闭时：释放连接池中的空闲连接
    close_db_pool()

#创建FastAPI应用
app = FastAPI(title="灵山景区导览系统", version="3.0", lifespan=lifespan)

#跨域中间件 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

#安全头中间件
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response

app.add_middleware(SecurityHeadersMiddleware)

#注册路由模块
app.include_router(user.router)
app.include_router(spots.router)
app.include_router(routes.router)
app.include_router(feedback.router)
app.include_router(favorites.router)
app.include_router(faq.router)
app.include_router(chat.router)
app.include_router(tts.router)
app.include_router(asr.router)
app.include_router(weather.router)
app.include_router(admin.router)

# ====================== 启动入口 ======================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
