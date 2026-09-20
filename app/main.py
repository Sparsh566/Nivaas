"""FastAPI application entry point. Legal routes registered before Gradio mount."""

import os
import time
import logging
from collections import defaultdict
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import gradio as gr

from app.config import settings
from app.legal.terms import render_terms
from app.legal.privacy import render_privacy

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Simple per-IP rate limiting
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 30
RATE_LIMIT_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old entries
    _rate_limits[client_ip] = [
        t for t in _rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limits[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Please wait a moment."},
        )

    _rate_limits[client_ip].append(now)
    response = await call_next(request)
    return response


# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Legal routes BEFORE Gradio mount
@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    return render_terms()


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    return render_privacy()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "tavily_configured": bool(settings.TAVILY_API_KEY),
        "demo_mode": settings.DEMO_MODE,
    }


# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s", settings.APP_NAME)
    try:
        from app.db.models import Base
        from app.db.engine import async_engine
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified")
    except Exception as e:
        logger.warning("Could not connect to database: %s. App will still run but caching is disabled.", str(e))


# Mount Gradio at root (AFTER legal routes)
from app.ui.app import create_gradio_app

gradio_app = create_gradio_app()
favicon_path = os.path.join(static_dir, "favicon.ico")
if not os.path.exists(favicon_path):
    favicon_path = os.path.join(static_dir, "favicon.svg")

app = gr.mount_gradio_app(
    app,
    gradio_app,
    path="/",
    favicon_path=favicon_path if os.path.exists(favicon_path) else None,
)
