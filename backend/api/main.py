"""Otakuflow API entry point.

Serves the JSON API under /api and the built frontend (if present).
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routers import analysis as analysis_router
from backend.api.routers import jobs as jobs_router
from backend.api.routers import pages, projects
from backend.api.routers import render as render_router
from backend.api.routers import script as script_router
from backend.api.routers import voice as voice_router
from backend.db.database import init_db
from backend.services.jobs import mark_interrupted_jobs

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("otakuflow")

ROOT = Path(__file__).resolve().parent.parent.parent
DIST = ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from backend.core import config as config_module

    config_module.validate_startup()
    db_file = init_db()
    interrupted = mark_interrupted_jobs()
    try:
        from backend.db.queries import projects as project_queries

        total = len(project_queries.list_projects())
    except Exception:
        total = "?"
    logger.info("[otakuflow] db=%s projects=%s interrupted=%s", db_file, total, interrupted)
    if not (DIST / "index.html").exists():
        logger.warning("[otakuflow] frontend/dist missing, run npm run build in frontend/")
    yield


app = FastAPI(title="Otakuflow", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

app.include_router(projects.router)
app.include_router(pages.router)
app.include_router(jobs_router.router)
app.include_router(analysis_router.router)
app.include_router(script_router.router)
app.include_router(voice_router.router)
app.include_router(render_router.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


if (DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
