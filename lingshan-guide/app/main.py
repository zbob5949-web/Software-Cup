from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_database
from app.routers import user, spots, routes, feedback, favorites, faq, chat,tts, asr, weather

app = FastAPI(title="灵山景区导览系统", version="3.0")

@app.on_event("startup")
def startup():
    init_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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