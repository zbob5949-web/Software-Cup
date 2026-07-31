from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（必须在任何 os.getenv 调用之前）
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from app.database import init_database
from app.routers import user, spots, routes, feedback, favorites, faq, chat, tts, asr, weather, digital_human, orders
from app.routers.admin import router as admin_router, ADMIN_HTML, PANEL_HTML

FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
FRONTEND_RESERVED_PREFIXES = ("api", "digital-human-3d", "live2d", "Resources")

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
app.include_router(orders.router)
app.include_router(tts.router)
app.include_router(asr.router)
app.include_router(weather.router)
app.include_router(digital_human.router)
app.include_router(admin_router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


@app.get("/admin", include_in_schema=False)
def admin_login():
    return HTMLResponse(ADMIN_HTML)


@app.get("/admin/panel", include_in_schema=False)
def admin_panel():
    return HTMLResponse(PANEL_HTML)


@app.get("/{full_path:path}", include_in_schema=False)
def frontend_app(full_path: str, request: Request):
    """Serve the built React app without intercepting backend-owned paths."""
    if not FRONTEND_DIST_DIR.is_dir():
        return Response(status_code=404)

    normalized_path = full_path.strip("/")
    if any(
        normalized_path == prefix or normalized_path.startswith(f"{prefix}/")
        for prefix in FRONTEND_RESERVED_PREFIXES
    ):
        return Response(status_code=404)

    frontend_root = FRONTEND_DIST_DIR.resolve()
    candidate = (FRONTEND_DIST_DIR / normalized_path).resolve()
    try:
        candidate.relative_to(frontend_root)
    except ValueError:
        return Response(status_code=404)

    if candidate.is_file():
        return FileResponse(candidate)

    index_path = frontend_root / "index.html"
    accepts_html = "text/html" in request.headers.get("accept", "")
    if index_path.is_file() and (not normalized_path or accepts_html):
        return FileResponse(index_path)

    return Response(status_code=404)
