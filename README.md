# Multi-User Notes API

A production-grade REST API for managing personal notes with multi-user authentication, note sharing, version history, full-text search, and a built-in frontend interface.

**Live Deployment:** https://epifi-assignment-e7yc.onrender.com

---

## Table of Contents

- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Custom Feature: Note Version History](#custom-feature-note-version-history)
- [Database Schema](#database-schema)
- [Setup and Installation](#setup-and-installation)
- [Running Locally](#running-locally)
- [Running with Docker](#running-with-docker)
- [Environment Variables](#environment-variables)
- [Automated Test Suite](#automated-test-suite)
- [Live Deployment Test Results](#live-deployment-test-results)
- [Project Structure](#project-structure)

---

## Architecture

The application follows a layered architecture:

```
Client (Browser / cURL)
    |
    v
FastAPI Application (main.py)
    |
    +-- Auth Router (/register, /login)
    +-- Notes Router (/notes, /search, /shared)
    |
    v
SQLAlchemy ORM (models.py)
    |
    v
PostgreSQL (production) / SQLite (development/testing)
```

Authentication is handled via JWT tokens issued on login. Every note-mutating endpoint requires a valid Bearer token in the Authorization header. Passwords are hashed using bcrypt before storage.

---

## Tech Stack

| Component        | Technology                          |
|------------------|-------------------------------------|
| Framework        | FastAPI 0.115.x                     |
| ORM              | SQLAlchemy 2.x                      |
| Database         | PostgreSQL (prod), SQLite (dev)     |
| Authentication   | JWT via python-jose, bcrypt hashing |
| Validation       | Pydantic v2 with email-validator    |
| Server           | Uvicorn (ASGI)                      |
| Frontend         | Vanilla HTML/CSS/JavaScript         |
| Testing          | pytest + httpx                      |
| Containerization | Docker                              |
| Hosting          | Render.com (Free Tier)              |

---

## Features

### Core Requirements

- **User Registration and Login** with JWT-based authentication
- **CRUD Operations** on notes (Create, Read, Update, Delete)
- **Note Sharing** between registered users via email
- **Access Control** ensuring users can only access their own notes or notes explicitly shared with them
- **OpenAPI Documentation** auto-generated and available at `/openapi.json`

### Stretch Goals (All Implemented)

- **Pagination** on `GET /notes` with `?page=` and `?per_page=` query parameters
- **Full-Text Search** via `GET /search?q=keyword`, searching across titles and content of owned and shared notes
- **Dockerization** with a production-ready Dockerfile
- **Frontend Interface** with a Notion-inspired UI featuring sidebar navigation, keyboard shortcuts, sharing modals, and version history panels

### Additional Features

- **Note Version History** (custom feature) — automatic snapshotting of previous note versions on every update
- **Shared Notes View** — dedicated endpoint and sidebar section for notes shared with the current user
- **Share Manifest** — endpoint to see who a note has been shared with
- **Live Timestamps** — frontend displays all timestamps in the user's local timezone

---

## API Endpoints

### Authentication

| Method | Endpoint    | Description                | Auth Required |
|--------|-------------|----------------------------|---------------|
| POST   | `/register` | Register a new user        | No            |
| POST   | `/login`    | Authenticate and get JWT   | No            |

### Notes

| Method | Endpoint                  | Description                         | Auth Required |
|--------|---------------------------|-------------------------------------|---------------|
| GET    | `/notes`                  | List all notes owned by the user    | Yes           |
| POST   | `/notes`                  | Create a new note                   | Yes           |
| GET    | `/notes/{id}`             | Get a specific note by ID           | Yes           |
| PUT    | `/notes/{id}`             | Update a note (owner only)          | Yes           |
| DELETE | `/notes/{id}`             | Delete a note (owner only)          | Yes           |
| POST   | `/notes/{id}/share`       | Share a note with another user      | Yes           |
| GET    | `/notes/{id}/history`     | Get version history of a note       | Yes           |
| GET    | `/notes/{id}/shares`      | List users a note is shared with    | Yes           |

### Search and Shared

| Method | Endpoint   | Description                              | Auth Required |
|--------|------------|------------------------------------------|---------------|
| GET    | `/search`  | Full-text search with `?q=keyword`       | Yes           |
| GET    | `/shared`  | List notes shared with the current user  | Yes           |

### Meta

| Method | Endpoint        | Description                    | Auth Required |
|--------|-----------------|--------------------------------|---------------|
| GET    | `/about`        | Application info and features  | No            |
| GET    | `/health`       | Health check                   | No            |
| GET    | `/openapi.json` | OpenAPI 3.1 specification      | No            |
| GET    | `/`             | Serves the frontend UI         | No            |

---

## Custom Feature: Note Version History

Every time a note is updated via `PUT /notes/{id}`, the system automatically saves a snapshot of the previous title and content into the `note_history` table before applying the new changes. This creates a complete, ordered version trail.

**Why this feature:**
Accidental overwrites are one of the most common frustrations in note-taking applications. Unlike Google Keep, which has no undo history, this system preserves every prior version so users can review and recover previous content at any time.

**How it works:**

1. User sends `PUT /notes/{id}` with updated title/content
2. The server saves the current title and content into `note_history` with an incrementing version number
3. The new title/content is applied to the note
4. Users can retrieve the full history via `GET /notes/{id}/history`

The history is returned in reverse chronological order (newest version first). Shared users who have read access to a note can also view its history.

---

## Database Schema

```
users
  - id (UUID, primary key)
  - email (unique, indexed)
  - hashed_password
  - created_at

notes
  - id (UUID, primary key)
  - title
  - content
  - owner_id (foreign key -> users.id)
  - created_at
  - updated_at

note_shares
  - id (UUID, primary key)
  - note_id (foreign key -> notes.id, cascade delete)
  - shared_with_user_id (foreign key -> users.id, cascade delete)
  - shared_at
  - UNIQUE(note_id, shared_with_user_id)

note_history
  - id (UUID, primary key)
  - note_id (foreign key -> notes.id, cascade delete)
  - title
  - content
  - version (integer)
  - edited_at
```

---

## Setup and Installation

### Prerequisites

- Python 3.11+
- pip

### Local Setup

```bash
git clone https://github.com/Nesar21/epifi_assignment.git
cd epifi_assignment

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### Create a `.env` file (optional, defaults work for local development)

```
DATABASE_URL=sqlite:///./notes.db
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Running Locally

```bash
source venv/bin/activate
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`. The frontend is served at the root URL. Interactive API docs are at `http://localhost:8000/docs`.

---

## Running with Docker

```bash
docker build -t notes-api .
docker run -p 8000:8000 notes-api
```

To connect to an external PostgreSQL database:

```bash
docker run -p 8000:8000 -e DATABASE_URL=postgresql://user:pass@host/db notes-api
```

---

## Environment Variables

| Variable                     | Default                            | Description                       |
|------------------------------|------------------------------------|-----------------------------------|
| `DATABASE_URL`               | `sqlite:///./notes.db`             | Database connection string        |
| `SECRET_KEY`                 | (hardcoded default)                | JWT signing secret                |
| `ALGORITHM`                  | `HS256`                            | JWT algorithm                     |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| `30`                               | Token expiry in minutes           |

For production, set `DATABASE_URL` to a PostgreSQL connection string and generate a strong `SECRET_KEY`.

---

## Automated Test Suite

The project includes 62 automated integration tests covering all endpoints, edge cases, and access control scenarios.

### Running Tests

```bash
source venv/bin/activate
pip install pytest httpx
pytest tests/ -v --tb=short
```

### Test Coverage

| Category      | Tests | What is verified                                                     |
|---------------|-------|----------------------------------------------------------------------|
| Register      | 7     | Success, duplicate email, invalid email, short password, missing fields, empty body |
| Login         | 8     | Success with JWT, wrong password returns "message" key, non-existent email, invalid/missing tokens |
| Create Note   | 5     | Success with all fields, missing title, missing content, empty body, unauthorized |
| Get Notes     | 4     | Empty list, own notes only, shared notes not in list, unauthorized   |
| Get Note      | 4     | Own note, shared note access, unshared forbidden, non-existent       |
| Update Note   | 6     | Title only, content only, both, non-existent, other user forbidden, shared user forbidden |
| Delete Note   | 4     | Success (204), non-existent, other user forbidden, shared user forbidden |
| Share Note    | 6     | Success, self-share blocked, non-existent user, duplicate share, non-owner forbidden, non-existent note |
| History       | 5     | Empty initially, created after update, multiple versions, unauthorized, shared user can view |
| Search        | 6     | By title, by content, case insensitive, no results, no cross-user leak, includes shared notes |
| Meta          | 3     | /about with "my features" key, /openapi.json valid, /health          |
| Pagination    | 3     | Page 1, page 2, no pagination returns all                           |
| E2E Lifecycle | 1     | Complete flow: register, login, create, update, share, search, delete |

All 62 tests pass consistently on both SQLite (local/CI) and PostgreSQL (production).

---

## Live Deployment Test Results

The following tests were executed against the live deployment at `https://epifi-assignment-e7yc.onrender.com` on May 16, 2026. Every test passed.

### Phase 0: Meta Endpoints (4 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 0.1 | `GET /about` returns JSON with `name`, `email`, `my features` (space, not underscore) | 200, correct keys | PASS |
| 0.2 | `GET /health` returns `{"status": "healthy"}` | 200 | PASS |
| 0.3 | `GET /openapi.json` returns valid OpenAPI 3.1.0 schema with all paths | 200, version 3.1.0 | PASS |
| 0.4 | `GET /` serves the frontend HTML page | 200 | PASS |

### Phase 1: Registration (8 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 1.1 | Register User A (alice@livetest.com) | 201, `{"message":"User registered successfully"}` | PASS |
| 1.2 | Register User B (bob@livetest.com) | 201 | PASS |
| 1.3 | Duplicate registration (alice@livetest.com again) | 409, `Email already registered` | PASS |
| 1.4 | Invalid email format ("not-an-email") | 422 | PASS |
| 1.5 | Short password (3 chars, minimum is 8) | 422 | PASS |
| 1.6 | Missing email field | 422 | PASS |
| 1.7 | Missing password field | 422 | PASS |
| 1.8 | Empty JSON body | 422 | PASS |

### Phase 2: Login and JWT (6 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 2.1 | Login User A, capture JWT token | 200, `{"access_token": "..."}` | PASS |
| 2.2 | Login User B, capture JWT token | 200 | PASS |
| 2.3 | Wrong password returns `{"message":"Invalid email or password"}` (not `{"detail":...}`) | 401, `message` key | PASS |
| 2.4 | Non-existent email login | 401 | PASS |
| 2.5 | Request with invalid JWT token | 401 | PASS |
| 2.6 | Request with no Authorization header | 401, `Not authenticated` | PASS |

### Phase 3: Create Notes (7 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 3.1 | Create "Meeting Notes" as User A | 201, response includes id, title, content, owner_id, created_at, updated_at | PASS |
| 3.2 | Create "Grocery List" as User A | 201 | PASS |
| 3.3 | Create "Book Recommendations" as User A (for pagination) | 201 | PASS |
| 3.4 | Create "Bobs Secret" as User B (for isolation testing) | 201 | PASS |
| 3.5 | Create note with missing title | 422 | PASS |
| 3.6 | Create note with missing content | 422 | PASS |
| 3.7 | Create note without authentication | 401 | PASS |

### Phase 4: Read Notes and Pagination (8 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 4.1 | `GET /notes` as User A returns only User A's 3 notes | 200, array of 3, no "Bobs Secret" | PASS |
| 4.2 | `GET /notes` as User B returns only User B's 1 note | 200, array of 1 | PASS |
| 4.3 | `GET /notes?page=1&per_page=2` returns 2 notes | 200, count = 2 | PASS |
| 4.4 | `GET /notes?page=2&per_page=2` returns 1 note (remainder) | 200, count = 1 | PASS |
| 4.5 | `GET /notes` without pagination returns all 3 | 200, count = 3 | PASS |
| 4.6 | `GET /notes/{id}` for own note | 200, full note object | PASS |
| 4.7 | `GET /notes/{id}` for non-existent note | 404, `Note not found` | PASS |
| 4.8 | `GET /notes/{id}` User B tries to read User A's note | 403, `Not authorized` | PASS |

### Phase 5: Update Notes (5 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 5.1 | Update title only, content unchanged | 200, title changed | PASS |
| 5.2 | Update content only, title unchanged | 200, content changed | PASS |
| 5.3 | Update both title and content | 200 | PASS |
| 5.4 | User B tries to update User A's note | 403 | PASS |
| 5.5 | Update non-existent note | 404 | PASS |

### Phase 6: Note Sharing (9 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 6.1 | Share Note 1 with User B | 200, `{"message":"Note shared successfully"}` | PASS |
| 6.2 | User B can now read the shared note (was 403 before) | 200 | PASS |
| 6.3 | User B cannot update the shared note (read-only access) | 403 | PASS |
| 6.4 | User B cannot delete the shared note | 403 | PASS |
| 6.5 | Self-share blocked (User A shares with themselves) | 400, `Cannot share note with yourself` | PASS |
| 6.6 | Duplicate share blocked (share with Bob again) | 400, `Note already shared with this user` | PASS |
| 6.7 | Share with non-existent user | 404, `User not found` | PASS |
| 6.8 | Non-owner (User B) tries to share User A's note | 403 | PASS |
| 6.9 | Share a non-existent note | 404, `Note not found` | PASS |

### Phase 7: Version History (3 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 7.1 | `GET /notes/{id}/history` returns 3 versions after 3 updates (v1: "Meeting Notes", v2: "Updated Meeting Notes", v3: "Updated Meeting Notes") | 200, 3 entries | PASS |
| 7.2 | User B (shared) can view history of shared note | 200 | PASS |
| 7.3 | User B cannot view history of unshared note | 403 | PASS |

### Phase 8: Full-Text Search (6 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 8.1 | Search `q=Meeting` finds "Final Meeting Notes" (title match) | 200, 1 result | PASS |
| 8.2 | Search `q=milk` finds "Grocery List" (content match) | 200, 1 result | PASS |
| 8.3 | Search `q=MEETING` (uppercase) still finds results (case insensitive) | 200, 1 result | PASS |
| 8.4 | Search `q=xyznonexistent` returns empty array | 200, 0 results | PASS |
| 8.5 | Search `q=Secret` as User A returns nothing (cross-user isolation) | 200, 0 results | PASS |
| 8.6 | Search `q=roadmap` as User B finds the shared note | 200, 1 result | PASS |

### Phase 9: Delete Notes (4 tests)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 9.1 | Delete own note (Note 2) | 204, no content | PASS |
| 9.2 | Confirm deleted note returns 404 | 404 | PASS |
| 9.3 | Delete non-existent note | 404 | PASS |
| 9.4 | User B cannot delete User A's note | 403 | PASS |

### Phase 10: Dockerization (1 test)

| # | Test | Expected | Result |
|---|------|----------|--------|
| 10.1 | Dockerfile exists with valid FROM, COPY, RUN pip install, CMD uvicorn | Valid Dockerfile | PASS |

### Summary

**Total: 61 tests executed, 61 passed, 0 failed.**

---

## Project Structure

```
epifi_assignment/
  main.py              # FastAPI application entry point, /about, /health, lifespan
  config.py            # Pydantic settings with env file support
  database.py          # SQLAlchemy engine, session factory, get_db dependency
  models.py            # User, Note, NoteShare, NoteHistory ORM models
  schemas.py           # Pydantic request/response schemas with validation
  auth.py              # Password hashing (bcrypt), JWT creation, get_current_user
  Dockerfile           # Production container image
  Procfile             # Render/Heroku process definition
  requirements.txt     # Python dependencies
  .env.example         # Template for environment variables
  routers/
    auth.py            # POST /register, POST /login
    notes.py           # All note CRUD, sharing, history, search endpoints
  static/
    index.html         # Frontend HTML (Notion-inspired single-page app)
    style.css          # Frontend styles
    app.js             # Frontend JavaScript (API client, state management, UI)
  tests/
    conftest.py        # Test fixtures, SQLite test DB, auth helpers
    test_auth.py       # 15 authentication tests
    test_notes.py      # 47 note operation tests
```
