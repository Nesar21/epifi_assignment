import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    shared_notes = relationship("NoteShare", back_populates="shared_with_user", cascade="all, delete-orphan")


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    owner = relationship("User", back_populates="notes")
    shares = relationship("NoteShare", back_populates="note", cascade="all, delete-orphan")
    history = relationship("NoteHistory", back_populates="note", cascade="all, delete-orphan", order_by="NoteHistory.version.desc()")


class NoteShare(Base):
    __tablename__ = "note_shares"

    id = Column(String, primary_key=True, default=generate_uuid)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    shared_with_user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    shared_at = Column(DateTime, default=utcnow)

    # Prevent duplicate shares
    __table_args__ = (
        UniqueConstraint("note_id", "shared_with_user_id", name="uq_note_share"),
    )

    # Relationships
    note = relationship("Note", back_populates="shares")
    shared_with_user = relationship("User", back_populates="shared_notes")


class NoteHistory(Base):
    __tablename__ = "note_history"

    id = Column(String, primary_key=True, default=generate_uuid)
    note_id = Column(String, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    version = Column(Integer, nullable=False)
    edited_at = Column(DateTime, default=utcnow)

    # Relationships
    note = relationship("Note", back_populates="history")
