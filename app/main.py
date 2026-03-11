"""
FastAPI application: CORS, lifespan (init_db), and API routers.
See docs/05_API_DESIGN.md.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from api.routes_articles import router as articles_router
from api.routes_keywords import router as keywords_router
from api.routes_scheduler import router as scheduler_router
from api.routes_usage import router as usage_router
from api.routes_settings import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    # teardown if needed


app = FastAPI(
    title="AI Content System API",
    description="Generate, manage, and publish SEO articles with AI",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(articles_router, prefix=PREFIX)
app.include_router(keywords_router, prefix=PREFIX)
app.include_router(scheduler_router, prefix=PREFIX)
app.include_router(usage_router, prefix=PREFIX)
app.include_router(settings_router, prefix=PREFIX)


@app.get("/health")
def health():
    """Service health (DB connectivity can be checked here)."""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """Readiness for receiving requests."""
    return {"status": "ready"}
