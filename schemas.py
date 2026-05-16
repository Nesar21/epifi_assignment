from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ── Auth Schemas ──────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    id: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str


# ── Note Schemas ──────────────────────────────────────────────


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    content: Optional[str] = Field(None, min_length=1)


class NoteResponse(BaseModel):
    id: str
    title: str
    content: str
    owner_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Share Schemas ─────────────────────────────────────────────


class NoteShareRequest(BaseModel):
    share_with_email: EmailStr


class NoteShareResponse(BaseModel):
    message: str


# ── History Schemas ───────────────────────────────────────────


class NoteHistoryResponse(BaseModel):
    id: str
    note_id: str
    title: str
    content: str
    version: int
    edited_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── About Schema ─────────────────────────────────────────────


class AboutResponse(BaseModel):
    name: str
    email: str
    my_features: dict = Field(..., alias="my features")

    model_config = ConfigDict(populate_by_name=True)


# ── Search Schema ────────────────────────────────────────────


class SearchResponse(BaseModel):
    notes: list[NoteResponse]
    query: str


# ── Message Schema ───────────────────────────────────────────


class MessageResponse(BaseModel):
    message: str
