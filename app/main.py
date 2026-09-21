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
from app.auth.router import router as auth_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, docs_url=None, redoc_url=None)


class VercelPathMiddleware:
    """ASGI middleware to restore the original request path when Vercel rewrites to /api/index.py."""

    def __init__(self, asgi_app):
        self.asgi_app = asgi_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.lower(): v for k, v in scope.get("headers", [])}
            serverless_destinations = {"/api/index.py", "/api/index", "/api/index.py/", "/api", "/api/"}
            restored_path = None

            # 1. Check query string for __path injected by vercel.json rewrite
            query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            if "__path=" in query_string:
                import urllib.parse
                for param in query_string.split("&"):
                    if param.startswith("__path="):
                        p = urllib.parse.unquote(param[7:]).split("?")[0].strip()
                        if p:
                            if not p.startswith("/"):
                                p = "/" + p
                            if p not in serverless_destinations:
                                restored_path = p
                                break

            # 2. Check edge headers injected by Vercel / proxies
            if not restored_path:
                candidates = [
                    headers.get(b"x-invoke-path"),
                    headers.get(b"x-forwarded-uri"),
                    headers.get(b"x-original-uri"),
                    headers.get(b"x-rewrite-url"),
                    headers.get(b"x-real-url"),
                    headers.get(b"x-matched-path"),
                    headers.get(b"x-vercel-matched-path"),
                ]
                for c in candidates:
                    if c:
                        p = c.decode("utf-8", errors="ignore").split("?")[0].strip()
                        if p:
                            if not p.startswith("/"):
                                p = "/" + p
                            # Only accept if it is not the serverless rewrite destination itself
                            if p not in serverless_destinations:
                                restored_path = p
                                break

            current_path = scope.get("path", "")
            if restored_path and restored_path != current_path:
                scope["path"] = restored_path
                scope["raw_path"] = restored_path.encode("ascii", errors="ignore")
        await self.asgi_app(scope, receive, send)


app.add_middleware(VercelPathMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
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

    forwarded = request.headers.get("x-forwarded-for")
    real_ip = request.headers.get("x-real-ip")
    client_ip = (
        (forwarded.split(",")[0].strip() if forwarded else None)
        or real_ip
        or (request.client.host if request.client else "unknown")
    )
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


from starlette.exceptions import HTTPException as StarletteHTTPException


# Request models
class ChatRequest(BaseModel):
    message: str
    state: Optional[dict] = None


@app.post("/api/chat")
@app.post("/chat")
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
@app.post("/emi")
async def emi_endpoint(args: CalculateEMIArgs):
    return await calculate_emi.execute(args)


@app.post("/api/compare")
@app.post("/compare")
async def compare_endpoint(args: ComparePropertiesArgs):
    return await compare_properties.execute(args)


# Authentication and User routes
app.include_router(auth_router)


# Main Single Page App (with route aliases for Vercel and local dev)
@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/api/", response_class=HTMLResponse)
@app.get("/api/index", response_class=HTMLResponse)
@app.get("/api/index.py", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/index", response_class=HTMLResponse)
async def index_page() -> HTMLResponse:
    possible_paths = [
        os.path.join(static_dir, "index.html"),
        os.path.join(os.path.dirname(__file__), "static", "index.html"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "static", "index.html"),
        os.path.join(os.getcwd(), "app", "static", "index.html"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Nivaas API is active</h1>")


# Fallback POST handler for serverless entry points (prevents 405 if rewrites mask the path)
@app.post("/api/index.py")
@app.post("/api/index")
@app.post("/api")
@app.post("/api/")
@app.post("/")
async def fallback_post_endpoint(request: Request):
    """Safely route POST requests arriving at serverless entry paths directly to their handler."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    if isinstance(body, dict) and "message" in body:
        req = ChatRequest(**body)
        return await chat_endpoint(req)
    elif isinstance(body, dict) and any(k in body for k in ("price_inr", "property_price", "annual_rate", "annual_interest_rate", "loan_amount")):
        # Normalize alternative keys
        if "property_price" in body and "price_inr" not in body:
            body["price_inr"] = body["property_price"]
        if "annual_interest_rate" in body and "annual_rate" not in body:
            body["annual_rate"] = body["annual_interest_rate"]
        args = CalculateEMIArgs(**body)
        return await emi_endpoint(args)
    elif isinstance(body, dict) and any(k in body for k in ("listing_ids", "properties")):
        if "properties" in body and "listing_ids" not in body:
            body["listing_ids"] = body["properties"]
        args = ComparePropertiesArgs(**body)
        return await compare_endpoint(args)
    elif isinstance(body, dict) and "email" in body and "password" in body:
        from app.auth.router import register, login, RegisterRequest, LoginRequest
        from fastapi import HTTPException
        res = Response()
        action = request.query_params.get("action", "").lower()
        path_param = request.query_params.get("__path", "").lower()
        is_register = (
            action == "register"
            or "register" in path_param
            or "full_name" in body
            or bool(body.get("full_name"))
        )
        try:
            if is_register:
                reg_data = {
                    "email": body["email"],
                    "password": body["password"],
                    "full_name": body.get("full_name"),
                }
                auth_res = await register(RegisterRequest(**reg_data), res)
            else:
                login_data = {
                    "email": body["email"],
                    "password": body["password"],
                }
                auth_res = await login(LoginRequest(**login_data), res)

            response = JSONResponse(content=auth_res.model_dump())
            for header, val in res.headers.items():
                if header.lower() == "set-cookie":
                    response.headers.append("set-cookie", val)
            return response
        except HTTPException as http_exc:
            return JSONResponse(
                status_code=http_exc.status_code,
                content={"detail": http_exc.detail},
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Authentication error: {str(e)}"},
            )

    return JSONResponse(
        status_code=400,
        content={"detail": "Unsupported POST payload on serverless entry point."},
    )


# 404 Fallback for HTML navigation requests (Single Page App routing)
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        accept = request.headers.get("accept", "")
        if "text/html" in accept:
            return await index_page()
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


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
