"""
FastAPI Root Application Entry Point
Mounts all project routers under /api/ai/<slug>/, manages CORS, security, and SSE streams.
"""
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from core.config import settings
from core.db import init_db
from core.health import health_router
from core.security import check_rate_limit, rate_limiter
from core.events import event_broker
from projects.p04_invoice.router import router as p04_router
from projects.p03_support.router import router as p03_router
from projects.p05_monitor.router import router as p05_router
from projects.p10_finance.router import router as p10_router
from projects.p02_legal.router import router as p02_router
from projects.p01_real_estate.router import router as p01_router
from projects.p07_voice.router import router as p07_router
from projects.p06_hr.router import router as p06_router
from projects.p09_media.router import router as p09_router
from projects.p08_competitor.router import router as p08_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    yield
    # Shutdown
    rate_limiter.cleanup()

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade AI Automation Systems Backend",
    version="3.5.0",
    lifespan=lifespan
)

# CORS Middleware configured strictly to allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount Core Health Router
app.include_router(health_router)
app.include_router(p04_router)
app.include_router(p03_router)
app.include_router(p05_router)
app.include_router(p10_router)
app.include_router(p02_router)
app.include_router(p01_router)
app.include_router(p07_router)
app.include_router(p06_router)
app.include_router(p09_router)
app.include_router(p08_router)

# Real-Time SSE Observability Stream Endpoint for "Under the Hood" UI drawer
@app.get("/api/ai/stream/{session_id}")
async def sse_event_stream(session_id: str):
    """Streams real-time execution steps and timings for a client session."""
    return StreamingResponse(
        event_broker.subscribe(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/health")
async def root_health():
    """Global system health probe."""
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "timestamp": time.time()
    }

# Global Exception Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": str(exc) if settings.DEBUG else "An unexpected server error occurred."
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
