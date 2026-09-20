"""FastAPI application entry point with high-performance REST API and static UI."""

import os
import time
import logging
from collections import defaultdict
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import settings
from app.legal.terms import render_terms
from app.legal.privacy import render_privacy
from app.agent.loop import AgentState, run_agent
from app.tools import calculate_emi, compare_properties
from app.tools.calculate_emi import CalculateEMIArgs
from app.tools.compare_properties import ComparePropertiesArgs

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

# Rate limiting (excludes static assets, localhost, and health checks)
_rate_limits: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT_REQUESTS = 300
RATE_LIMIT_WINDOW = 60  # seconds


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if (
        path.startswith(("/static", "/assets", "/favicon"))
        or path in ("/", "/health", "/api/health", "/terms", "/privacy")
        or "." in path.split("/")[-1]
    ):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    if client_ip in ("127.0.0.1", "localhost", "::1"):
        return await call_next(request)

    now = time.time()
    _rate_limits[client_ip] = [
        t for t in _rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(_rate_limits[client_ip]) >= RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content={"error": "Too many requests. Please wait a moment."},
        )

    _rate_limits[client_ip].append(now)
    return await call_next(request)


# Static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Legal routes
@app.get("/terms", response_class=HTMLResponse)
async def terms_page():
    return render_terms()


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_page():
    return render_privacy()


@app.get("/health")
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "groq_configured": bool(settings.GROQ_API_KEY),
        "tavily_configured": bool(settings.TAVILY_API_KEY),
        "demo_mode": settings.DEMO_MODE,
    }


# Request models
class ChatRequest(BaseModel):
    message: str
    state: Optional[dict] = None


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Conversational endpoint: processes query through agent loop."""
    state = AgentState.from_dict(req.state or {})
    response, state = await run_agent(req.message, state)
    return {
        "response": response,
        "state": state.to_dict(),
        "shortlist": state.last_shortlist,
        "requirements": state.requirements,
        "weights": state.weights,
        "agent_steps": state.agent_steps,
        "is_demo": state.is_demo,
    }


@app.post("/api/emi")
async def emi_endpoint(args: CalculateEMIArgs):
    return await calculate_emi.execute(args)


@app.post("/api/compare")
async def compare_endpoint(args: ComparePropertiesArgs):
    return await compare_properties.execute(args)


# Main Single Page App
@app.get("/", response_class=HTMLResponse)
async def index_page():
    possible_paths = [
        os.path.join(static_dir, "index.html"),
        os.path.join(os.path.dirname(__file__), "static", "index.html"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "index.html"),
        os.path.join(os.getcwd(), "app", "static", "index.html"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
    return HTMLResponse("<h1>Nivaas API is active</h1>")


# Initialize database tables on startup (with graceful fallback)
@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s", settings.APP_NAME)
    if os.environ.get("VERCEL") or "localhost" in settings.DATABASE_URL:
        logger.info("Serverless environment or local DB default detected. Skipping startup DB block.")
        return

    try:
        import asyncio
        from app.db.models import Base
        from app.db.engine import async_engine

        async def init_db():
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        await asyncio.wait_for(init_db(), timeout=2.0)
        logger.info("Database tables verified")
    except Exception as e:
        logger.warning("Database unavailable (%s). Continuing in serverless/in-memory mode.", str(e))
