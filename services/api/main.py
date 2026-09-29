from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import init_db
from app.logging import configure_logging
from app.routers.frames import router as frames_router
from app.routers.jobs import router as jobs_router

settings = get_settings()
configure_logging(settings.log_level)
init_db()

app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://news.tathyaforge.in",
        "https://news.tathyaforge.in",
    ],
    allow_origin_regex=r"https?://((localhost|127\.0\.0\.1|news\.tathyaforge\.in)|((192\.168|10)\.\d{1,3}\.\d{1,3}\.\d{1,3})|(172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}))(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(jobs_router)
app.include_router(frames_router)


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "app": settings.app_name,
        "mock_ai": settings.mock_ai,
        "storage": str(settings.jobs_dir),
    }


@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "detail": "Something went wrong. Check server logs."},
    )
