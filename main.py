from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import Base, engine
from routers import auth, notes

# ── Create tables on startup ─────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── App init ──────────────────────────────────────────────────
app = FastAPI(
    title="Notes API",
    description="Multi-user notes service with sharing, version history, and search.",
    version="1.0.0",
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
app.mount("/static", StaticFiles(directory="static"), name="static")


# ── GET /about ───────────────────────────────────────────────
@app.get("/about")
def about():
    return {
        "name": "YOUR_NAME_HERE",
        "email": "YOUR_EMAIL_HERE",
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
    return FileResponse("static/index.html")
