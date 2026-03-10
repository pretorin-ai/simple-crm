import logging
import os
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import SessionLocal, get_db
from app.logging_config import generate_request_id, request_id_ctx, setup_logging
from app.routers import (
    accounts,
    attachments,
    audit,
    auth,
    capture_notes,
    communications,
    compliance,
    contacts,
    contacts_followup,
    contracts,
    gmail,
    opportunities,
    proposals,
    sam_gov,
    teaming,
    timeline,
    users,
    vehicles,
)
from app.seed_data import seed_database

# Initialize Sentry (no-op if DSN not configured)
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:  # pragma: no cover
    sentry_sdk.init(
        dsn=_sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
    )

# Configure structured JSON logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID to every request for log correlation."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        rid = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_ctx.set(rid)
        try:
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = rid
            return response
        finally:
            request_id_ctx.reset(token)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed database (schema managed by Alembic migrations via entrypoint.sh)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Pretorin CRM API",
    description="API for managing sales contacts and government contract opportunities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter

# Request ID middleware (outermost so all middleware/handlers have the ID)
app.add_middleware(RequestIdMiddleware)

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all handler so unhandled errors always return JSON."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Disable favicon
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return {"detail": "Not Found"}


# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [frontend_url]
extra_origins = os.getenv("EXTRA_CORS_ORIGINS", "")
if extra_origins:
    allowed_origins.extend(o.strip() for o in extra_origins.split(",") if o.strip())
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers - specific paths before parameterized ones
app.include_router(auth.router)
app.include_router(contacts_followup.router)
app.include_router(contacts.router)
app.include_router(communications.router)
app.include_router(contracts.router)
app.include_router(accounts.router)
app.include_router(opportunities.router)
app.include_router(timeline.router)
app.include_router(capture_notes.router)
app.include_router(attachments.router)
app.include_router(vehicles.router)
app.include_router(teaming.router)
app.include_router(proposals.router)
app.include_router(compliance.router)
app.include_router(sam_gov.router)
app.include_router(gmail.router)
app.include_router(users.router)
app.include_router(audit.router)


@app.get("/")
def root():
    """API root endpoint"""
    return {"message": "Pretorin CRM API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint — verifies database connectivity."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": "database unreachable"},
        )
    return {"status": "healthy"}
