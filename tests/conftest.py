"""
Test fixtures — SQLite in-memory database for isolated, fast testing.
Each test function gets a fresh DB + client.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app

# ── In-memory SQLite for tests ──
TEST_DB_URL = "sqlite:///./test_notes.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """TestClient with overridden DB dependency."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Auth Helpers ──


def register_user(client: TestClient, email: str = "alice@test.com", password: str = "securepass123"):
    """Register a user, return response."""
    return client.post("/register", json={"email": email, "password": password})


def login_user(client: TestClient, email: str = "alice@test.com", password: str = "securepass123"):
    """Login a user, return the access token."""
    res = client.post("/login", json={"email": email, "password": password})
    return res.json().get("access_token")


def auth_header(token: str):
    """Return Authorization header dict."""
    return {"Authorization": f"Bearer {token}"}


def create_authenticated_user(client: TestClient, email: str = "alice@test.com", password: str = "securepass123"):
    """Register + login, return token."""
    register_user(client, email, password)
    return login_user(client, email, password)
