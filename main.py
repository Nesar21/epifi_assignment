import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from database import Base, engine
from routers import auth, notes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    logger.info("Starting up — creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise
    yield


# ── App init ──────────────────────────────────────────────────
app = FastAPI(
    title="Notes API",
    description="Multi-user notes service with sharing, version history, and search.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (allow all for automated testing) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ──────────────────────────────────────────
app.include_router(auth.router)
app.include_router(notes.router)

# ── Mount static files ───────────────────────────────────────
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ── GET /about ───────────────────────────────────────────────
@app.get("/about")
def about():
    return {
        "name": "Nesar",
        "email": "nesar21@github.com",
        "my features": {
            "Note Version History": (
                "Every edit to a note automatically saves the previous version. "
                "Users can view all past versions via GET /notes/{id}/history. "
                "Designed for undo/recovery when notes are accidentally overwritten — "
                "a common pain point in note-taking apps like Google Keep."
            ),
        },
    }


# ── Health check ─────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "healthy"}


# ── Serve frontend ───────────────────────────────────────────
@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(os.path.join(static_dir, "index.html"))
