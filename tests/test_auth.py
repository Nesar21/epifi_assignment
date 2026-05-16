"""
Authentication endpoint tests — covers every spec requirement + edge case.
Maps to: POST /register, POST /login
"""
from tests.conftest import register_user, login_user, auth_header, create_authenticated_user


# ═══════════════════════════════════════════════════════
# POST /register
# ═══════════════════════════════════════════════════════

class TestRegister:
    def test_register_success(self, client):
        """Register returns 201 with correct message."""
        res = register_user(client)
        assert res.status_code == 201
        assert res.json()["message"] == "User registered successfully"

    def test_register_duplicate_email(self, client):
        """Duplicate email returns 409."""
        register_user(client, "dup@test.com")
        res = register_user(client, "dup@test.com")
        assert res.status_code == 409
        assert "already registered" in res.json()["detail"].lower()

    def test_register_invalid_email(self, client):
        """Invalid email format returns 422."""
        res = client.post("/register", json={"email": "not-an-email", "password": "securepass123"})
        assert res.status_code == 422

    def test_register_short_password(self, client):
        """Password < 8 chars returns 422."""
        res = client.post("/register", json={"email": "short@test.com", "password": "abc"})
        assert res.status_code == 422

    def test_register_missing_email(self, client):
        """Missing email returns 422."""
        res = client.post("/register", json={"password": "securepass123"})
        assert res.status_code == 422

    def test_register_missing_password(self, client):
        """Missing password returns 422."""
        res = client.post("/register", json={"email": "nopass@test.com"})
        assert res.status_code == 422

    def test_register_empty_body(self, client):
        """Empty body returns 422."""
        res = client.post("/register", json={})
        assert res.status_code == 422


# ═══════════════════════════════════════════════════════
# POST /login
# ═══════════════════════════════════════════════════════

class TestLogin:
    def test_login_success(self, client):
        """Login returns 200 with access_token."""
        register_user(client)
        res = client.post("/login", json={"email": "alice@test.com", "password": "securepass123"})
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_login_wrong_password(self, client):
        """Wrong password returns 401 with {"message": ...}."""
        register_user(client)
        res = client.post("/login", json={"email": "alice@test.com", "password": "wrongpassword"})
        assert res.status_code == 401
        # SPEC: must be "message" not "detail"
        assert "message" in res.json()
        assert "invalid" in res.json()["message"].lower()

    def test_login_nonexistent_email(self, client):
        """Non-existent email returns 401."""
        res = client.post("/login", json={"email": "ghost@test.com", "password": "anypassword1"})
        assert res.status_code == 401
        assert "message" in res.json()

    def test_login_invalid_email_format(self, client):
        """Invalid email format on login returns 422."""
        res = client.post("/login", json={"email": "not-email", "password": "securepass123"})
        assert res.status_code == 422

    def test_login_missing_fields(self, client):
        """Missing login fields returns 422."""
        res = client.post("/login", json={})
        assert res.status_code == 422

    def test_jwt_token_works(self, client):
        """Token from login can access protected routes."""
        token = create_authenticated_user(client)
        res = client.get("/notes", headers=auth_header(token))
        assert res.status_code == 200

    def test_invalid_token_rejected(self, client):
        """Garbage token returns 401."""
        res = client.get("/notes", headers=auth_header("garbage.token.here"))
        assert res.status_code == 401

    def test_missing_token_rejected(self, client):
        """No Authorization header returns 401."""
        res = client.get("/notes")
        assert res.status_code in (401, 403)
