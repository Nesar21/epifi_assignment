from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from auth import get_current_user
from database import get_db
from models import Note, NoteHistory, NoteShare, User
from schemas import (
    NoteCreate,
    NoteHistoryResponse,
    NoteResponse,
    NoteShareRequest,
    NoteUpdate,
    MessageResponse,
)

router = APIRouter(tags=["Notes"])


# ── Helper ────────────────────────────────────────────────────


def get_note_or_404(note_id: str, db: Session) -> Note:
    """Fetch a note by ID or raise 404."""
    note = db.query(Note).filter(Note.id == note_id).first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


def check_note_access(note: Note, user: User, db: Session) -> bool:
    """Check if user owns the note or has it shared with them."""
    if note.owner_id == user.id:
        return True
    share = (
        db.query(NoteShare)
        .filter(NoteShare.note_id == note.id, NoteShare.shared_with_user_id == user.id)
        .first()
    )
    return share is not None


def check_owner_only(note: Note, user: User):
    """Check if user is the owner. Raises 403 if not."""
    if note.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this note",
        )


# ── GET /notes ────────────────────────────────────────────────


@router.get("/notes", response_model=list[NoteResponse])
def get_all_notes(
    page: Optional[int] = Query(None, ge=1),
    per_page: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notes created by the authenticated user.
    Strict spec: only owned notes (shared notes accessible via GET /notes/{id}).
    Supports optional pagination with ?page=1&per_page=10.
    """
    query = db.query(Note).filter(Note.owner_id == current_user.id).order_by(Note.created_at.desc())

    # Pagination (optional — if page param provided)
    if page is not None and per_page is not None:
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)

    notes = query.all()
    return notes


# ── GET /notes/{id} ──────────────────────────────────────────


@router.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific note by ID. User must own it or have it shared with them."""
    note = get_note_or_404(note_id, db)

    if not check_note_access(note, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this note",
        )

    return note


# ── POST /notes ──────────────────────────────────────────────


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new note for the authenticated user."""
    new_note = Note(
        title=note_data.title,
        content=note_data.content,
        owner_id=current_user.id,
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note


# ── PUT /notes/{id} ──────────────────────────────────────────


@router.put("/notes/{note_id}", response_model=NoteResponse)
def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing note. Only the owner can update.
    Saves the previous version to NoteHistory before overwriting (custom feature).
    """
    note = get_note_or_404(note_id, db)
    check_owner_only(note, current_user)

    # ── Save current version to history before update ──
    # Count existing history entries to determine version number
    current_version = (
        db.query(NoteHistory).filter(NoteHistory.note_id == note.id).count() + 1
    )

    history_entry = NoteHistory(
        note_id=note.id,
        title=note.title,
        content=note.content,
        version=current_version,
    )
    db.add(history_entry)

    # ── Apply updates ──
    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content

    db.commit()
    db.refresh(note)
    return note


# ── DELETE /notes/{id} ───────────────────────────────────────


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a note. Only the owner can delete (not shared users).
    Cascade deletes all shares and history for this note.
    """
    note = get_note_or_404(note_id, db)
    check_owner_only(note, current_user)

    db.delete(note)
    db.commit()
    return None


# ── POST /notes/{id}/share ───────────────────────────────────


@router.post("/notes/{note_id}/share", response_model=MessageResponse)
def share_note(
    note_id: str,
    share_data: NoteShareRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Share a note with another user by email. Only the owner can share."""
    note = get_note_or_404(note_id, db)
    check_owner_only(note, current_user)

    # Find target user
    target_user = db.query(User).filter(User.email == share_data.share_with_email).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Cannot share with yourself
    if target_user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share note with yourself",
        )

    # Check if already shared
    existing_share = (
        db.query(NoteShare)
        .filter(
            NoteShare.note_id == note.id,
            NoteShare.shared_with_user_id == target_user.id,
        )
        .first()
    )
    if existing_share:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note already shared with this user",
        )

    # Create share
    new_share = NoteShare(
        note_id=note.id,
        shared_with_user_id=target_user.id,
    )
    db.add(new_share)
    db.commit()

    return {"message": "Note shared successfully"}


# ── GET /notes/{id}/history ──────────────────────────────────


@router.get("/notes/{note_id}/history", response_model=list[NoteHistoryResponse])
def get_note_history(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get version history for a note. User must own it or have it shared with them."""
    note = get_note_or_404(note_id, db)

    if not check_note_access(note, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this note",
        )

    history = (
        db.query(NoteHistory)
        .filter(NoteHistory.note_id == note.id)
        .order_by(NoteHistory.version.desc())
        .all()
    )
    return history


# ── GET /search ──────────────────────────────────────────────


@router.get("/search", response_model=list[NoteResponse])
def search_notes(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Full-text search across notes the user owns or has shared access to.
    Uses ilike for portability across SQLite (tests) and PostgreSQL (production).
    """
    search_pattern = f"%{q}%"

    # Get IDs of notes shared with current user
    shared_note_ids = (
        db.query(NoteShare.note_id)
        .filter(NoteShare.shared_with_user_id == current_user.id)
    )

    # Search in owned + shared notes
    notes = (
        db.query(Note)
        .filter(
            or_(
                Note.owner_id == current_user.id,
                Note.id.in_(shared_note_ids),
            ),
            or_(
                Note.title.ilike(search_pattern),
                Note.content.ilike(search_pattern),
            ),
        )
        .order_by(Note.updated_at.desc())
        .all()
    )
    return notes


# ── GET /shared (Frontend helper — notes shared with me) ─────


@router.get("/shared", response_model=list[NoteResponse])
def get_shared_notes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notes that have been shared WITH the current user.
    This is a frontend helper endpoint — not in the assignment spec.
    """
    shared_note_ids = (
        db.query(NoteShare.note_id)
        .filter(NoteShare.shared_with_user_id == current_user.id)
    )
    notes = (
        db.query(Note)
        .filter(Note.id.in_(shared_note_ids))
        .order_by(Note.updated_at.desc())
        .all()
    )
    return notes


# ── GET /notes/{id}/shares (Frontend helper — who is it shared with) ──


@router.get("/notes/{note_id}/shares")
def get_note_shares(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get list of users a note is shared with. Only owner can see this."""
    note = get_note_or_404(note_id, db)
    check_owner_only(note, current_user)

    shares = (
        db.query(NoteShare)
        .filter(NoteShare.note_id == note.id)
        .all()
    )

    result = []
    for share in shares:
        user = db.query(User).filter(User.id == share.shared_with_user_id).first()
        if user:
            result.append({
                "email": user.email,
                "shared_at": share.shared_at.isoformat() if share.shared_at else None,
                "access": "read",
            })
    return result
