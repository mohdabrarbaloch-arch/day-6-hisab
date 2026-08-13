"""Hisab app assembly: FastAPI + CORS + rate limiting + static SPA."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import init_db
from app.deps import limiter
from app.routers import auth, clients, invoices, stats

# Resolve the static dir from this file's own location instead of the process
# working directory. Vercel's serverless Python runtime runs from a different
# CWD, so a relative path like "app/static" silently resolves to nothing there
# and the SPA comes back blank. Anchoring to __file__ makes it work everywhere.
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    # create_all is idempotent, so this is safe across cold starts and
    # concurrent serverless instances. We also call init_db() at import time in
    # app.database because Vercel's Python runtime does not reliably run the
    # lifespan handler — this here is the belt-and-suspenders path.
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": "1.0.0"}


app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(invoices.router)
app.include_router(stats.router)

# Static SPA — mounted last so /api/* routes always win.
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


# Guarantee tables exist at import time. Vercel's serverless Python runtime
# imports this module and serves requests WITHOUT running the lifespan handler,
# so create_all must happen here (after every router/model is imported above)
# or the first request on a cold start fails with "no such table: users".
init_db()
