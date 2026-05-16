"""
Notes CRUD + Share + History + Search + Pagination tests.
Covers every endpoint and edge case from the assignment spec.
"""
from tests.conftest import register_user, auth_header, create_authenticated_user


# ── Helpers ──

def create_note(client, token, title="My Note", content="Some content"):
    return client.post("/notes", json={"title": title, "content": content}, headers=auth_header(token))


def make_two_users(client):
    """Create Alice and Bob, return their tokens."""
    alice = create_authenticated_user(client, "alice@test.com")
    bob = create_authenticated_user(client, "bob@test.com")
    return alice, bob


# ═══════════════════════════════════════════════════════
# POST /notes — Create
# ═══════════════════════════════════════════════════════

class TestCreateNote:
    def test_create_success(self, client):
        token = create_authenticated_user(client)
        res = create_note(client, token)
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "My Note"
        assert data["content"] == "Some content"
        assert "id" in data
        assert "owner_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_missing_title(self, client):
        token = create_authenticated_user(client)
        res = client.post("/notes", json={"content": "no title"}, headers=auth_header(token))
        assert res.status_code == 422

    def test_create_missing_content(self, client):
        token = create_authenticated_user(client)
        res = client.post("/notes", json={"title": "no content"}, headers=auth_header(token))
        assert res.status_code == 422

    def test_create_empty_body(self, client):
        token = create_authenticated_user(client)
        res = client.post("/notes", json={}, headers=auth_header(token))
        assert res.status_code == 422

    def test_create_unauthorized(self, client):
        res = client.post("/notes", json={"title": "x", "content": "y"})
        assert res.status_code in (401, 403)


# ═══════════════════════════════════════════════════════
# GET /notes — List own notes
# ═══════════════════════════════════════════════════════

class TestGetNotes:
    def test_empty_list(self, client):
        token = create_authenticated_user(client)
        res = client.get("/notes", headers=auth_header(token))
        assert res.status_code == 200
        assert res.json() == []

    def test_returns_own_notes_only(self, client):
        alice, bob = make_two_users(client)
        create_note(client, alice, "Alice Note", "Alice content")
        create_note(client, bob, "Bob Note", "Bob content")

        res = client.get("/notes", headers=auth_header(alice))
        notes = res.json()
        assert len(notes) == 1
        assert notes[0]["title"] == "Alice Note"

    def test_shared_notes_not_in_list(self, client):
        """Spec: GET /notes returns only OWNED notes. Shared notes via GET /notes/{id}."""
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        # Share with Bob
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        # Bob's GET /notes should NOT include Alice's note
        res = client.get("/notes", headers=auth_header(bob))
        assert len(res.json()) == 0

    def test_unauthorized(self, client):
        res = client.get("/notes")
        assert res.status_code in (401, 403)


# ═══════════════════════════════════════════════════════
# GET /notes/{id} — Get single note
# ═══════════════════════════════════════════════════════

class TestGetNote:
    def test_get_own_note(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.get(f"/notes/{note['id']}", headers=auth_header(token))
        assert res.status_code == 200
        assert res.json()["id"] == note["id"]

    def test_get_shared_note(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.get(f"/notes/{note['id']}", headers=auth_header(bob))
        assert res.status_code == 200

    def test_get_unshared_note_forbidden(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.get(f"/notes/{note['id']}", headers=auth_header(bob))
        assert res.status_code == 403

    def test_get_nonexistent(self, client):
        token = create_authenticated_user(client)
        res = client.get("/notes/nonexistent-id-123", headers=auth_header(token))
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════
# PUT /notes/{id} — Update
# ═══════════════════════════════════════════════════════

class TestUpdateNote:
    def test_update_title(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.put(f"/notes/{note['id']}", json={"title": "Updated"}, headers=auth_header(token))
        assert res.status_code == 200
        assert res.json()["title"] == "Updated"
        assert res.json()["content"] == "Some content"  # unchanged

    def test_update_content(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.put(f"/notes/{note['id']}", json={"content": "New body"}, headers=auth_header(token))
        assert res.status_code == 200
        assert res.json()["content"] == "New body"

    def test_update_both(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.put(f"/notes/{note['id']}", json={"title": "T2", "content": "C2"}, headers=auth_header(token))
        assert res.status_code == 200
        assert res.json()["title"] == "T2"
        assert res.json()["content"] == "C2"

    def test_update_nonexistent(self, client):
        token = create_authenticated_user(client)
        res = client.put("/notes/fake-id", json={"title": "x"}, headers=auth_header(token))
        assert res.status_code == 404

    def test_update_other_users_note(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.put(f"/notes/{note['id']}", json={"title": "hacked"}, headers=auth_header(bob))
        assert res.status_code == 403

    def test_shared_user_cannot_update(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.put(f"/notes/{note['id']}", json={"title": "hacked"}, headers=auth_header(bob))
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════
# DELETE /notes/{id}
# ═══════════════════════════════════════════════════════

class TestDeleteNote:
    def test_delete_success(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.delete(f"/notes/{note['id']}", headers=auth_header(token))
        assert res.status_code == 204
        # Verify gone
        res2 = client.get(f"/notes/{note['id']}", headers=auth_header(token))
        assert res2.status_code == 404

    def test_delete_nonexistent(self, client):
        token = create_authenticated_user(client)
        res = client.delete("/notes/fake-id", headers=auth_header(token))
        assert res.status_code == 404

    def test_delete_other_users_note(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.delete(f"/notes/{note['id']}", headers=auth_header(bob))
        assert res.status_code == 403

    def test_shared_user_cannot_delete(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.delete(f"/notes/{note['id']}", headers=auth_header(bob))
        assert res.status_code == 403


# ═══════════════════════════════════════════════════════
# POST /notes/{id}/share
# ═══════════════════════════════════════════════════════

class TestShareNote:
    def test_share_success(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.post(f"/notes/{note['id']}/share",
                           json={"share_with_email": "bob@test.com"},
                           headers=auth_header(alice))
        assert res.status_code == 200
        assert "shared" in res.json()["message"].lower()

    def test_share_with_self(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.post(f"/notes/{note['id']}/share",
                           json={"share_with_email": "alice@test.com"},
                           headers=auth_header(token))
        assert res.status_code == 400

    def test_share_nonexistent_user(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.post(f"/notes/{note['id']}/share",
                           json={"share_with_email": "ghost@test.com"},
                           headers=auth_header(token))
        assert res.status_code == 404

    def test_share_duplicate(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.post(f"/notes/{note['id']}/share",
                           json={"share_with_email": "bob@test.com"},
                           headers=auth_header(alice))
        assert res.status_code == 400

    def test_share_not_owner(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.post(f"/notes/{note['id']}/share",
                           json={"share_with_email": "alice@test.com"},
                           headers=auth_header(bob))
        assert res.status_code == 403

    def test_share_nonexistent_note(self, client):
        token = create_authenticated_user(client)
        register_user(client, "bob@test.com")
        res = client.post("/notes/fake-id/share",
                           json={"share_with_email": "bob@test.com"},
                           headers=auth_header(token))
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════
# GET /notes/{id}/history — Version History (Custom Feature)
# ═══════════════════════════════════════════════════════

class TestHistory:
    def test_no_history_initially(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token).json()
        res = client.get(f"/notes/{note['id']}/history", headers=auth_header(token))
        assert res.status_code == 200
        assert res.json() == []

    def test_history_after_update(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token, "V1 Title", "V1 Content").json()
        client.put(f"/notes/{note['id']}", json={"title": "V2 Title", "content": "V2 Content"}, headers=auth_header(token))
        res = client.get(f"/notes/{note['id']}/history", headers=auth_header(token))
        assert res.status_code == 200
        history = res.json()
        assert len(history) == 1
        assert history[0]["title"] == "V1 Title"
        assert history[0]["content"] == "V1 Content"
        assert history[0]["version"] == 1

    def test_multiple_versions(self, client):
        token = create_authenticated_user(client)
        note = create_note(client, token, "V1", "C1").json()
        client.put(f"/notes/{note['id']}", json={"title": "V2", "content": "C2"}, headers=auth_header(token))
        client.put(f"/notes/{note['id']}", json={"title": "V3", "content": "C3"}, headers=auth_header(token))
        res = client.get(f"/notes/{note['id']}/history", headers=auth_header(token))
        history = res.json()
        assert len(history) == 2
        # Most recent version first (desc order)
        assert history[0]["version"] == 2
        assert history[1]["version"] == 1

    def test_history_unauthorized(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        res = client.get(f"/notes/{note['id']}/history", headers=auth_header(bob))
        assert res.status_code == 403

    def test_history_shared_user_can_view(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice).json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.get(f"/notes/{note['id']}/history", headers=auth_header(bob))
        assert res.status_code == 200


# ═══════════════════════════════════════════════════════
# GET /search?q=keyword — Full-text Search (Stretch Goal)
# ═══════════════════════════════════════════════════════

class TestSearch:
    def test_search_by_title(self, client):
        token = create_authenticated_user(client)
        create_note(client, token, "Python Tutorial", "Learn Python basics")
        create_note(client, token, "Go Tutorial", "Learn Go basics")
        res = client.get("/search?q=Python", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 1
        assert res.json()[0]["title"] == "Python Tutorial"

    def test_search_by_content(self, client):
        token = create_authenticated_user(client)
        create_note(client, token, "Shopping", "Buy bananas and milk")
        res = client.get("/search?q=bananas", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_search_case_insensitive(self, client):
        token = create_authenticated_user(client)
        create_note(client, token, "UPPERCASE NOTE", "some content here")
        res = client.get("/search?q=uppercase", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_search_no_results(self, client):
        token = create_authenticated_user(client)
        create_note(client, token, "My Note", "Some content")
        res = client.get("/search?q=xyznonexistent", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_search_doesnt_show_others_notes(self, client):
        alice, bob = make_two_users(client)
        create_note(client, alice, "Secret Alice Note", "Alice private data")
        res = client.get("/search?q=Alice", headers=auth_header(bob))
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_search_shows_shared_notes(self, client):
        alice, bob = make_two_users(client)
        note = create_note(client, alice, "Shared Doc", "Shared content xyz").json()
        client.post(f"/notes/{note['id']}/share",
                     json={"share_with_email": "bob@test.com"},
                     headers=auth_header(alice))
        res = client.get("/search?q=xyz", headers=auth_header(bob))
        assert res.status_code == 200
        assert len(res.json()) == 1


# ═══════════════════════════════════════════════════════
# GET /about, GET /openapi.json, GET /health — Meta Endpoints
# ═══════════════════════════════════════════════════════

class TestMetaEndpoints:
    def test_about(self, client):
        res = client.get("/about")
        assert res.status_code == 200
        data = res.json()
        assert "name" in data
        assert "email" in data
        # SPEC: key is "my features" with space, not underscore
        assert "my features" in data

    def test_openapi_json(self, client):
        res = client.get("/openapi.json")
        assert res.status_code == 200
        data = res.json()
        assert "openapi" in data
        assert "paths" in data
        # Check key paths exist
        assert "/register" in data["paths"]
        assert "/login" in data["paths"]
        assert "/notes" in data["paths"]
        assert "/about" in data["paths"]

    def test_health(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"


# ═══════════════════════════════════════════════════════
# Pagination (Stretch Goal)
# ═══════════════════════════════════════════════════════

class TestPagination:
    def test_pagination_page_1(self, client):
        token = create_authenticated_user(client)
        for i in range(5):
            create_note(client, token, f"Note {i}", f"Content {i}")
        res = client.get("/notes?page=1&per_page=2", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_pagination_page_2(self, client):
        token = create_authenticated_user(client)
        for i in range(5):
            create_note(client, token, f"Note {i}", f"Content {i}")
        res = client.get("/notes?page=2&per_page=2", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_no_pagination_returns_all(self, client):
        token = create_authenticated_user(client)
        for i in range(5):
            create_note(client, token, f"Note {i}", f"Content {i}")
        res = client.get("/notes", headers=auth_header(token))
        assert res.status_code == 200
        assert len(res.json()) == 5


# ═══════════════════════════════════════════════════════
# Full E2E Lifecycle
# ═══════════════════════════════════════════════════════

class TestE2ELifecycle:
    def test_complete_flow(self, client):
        """End-to-end: register → login → create → update → share → history → search → delete."""
        # 1. Register Alice
        r = client.post("/register", json={"email": "alice@e2e.com", "password": "password123"})
        assert r.status_code == 201

        # 2. Register Bob
        r = client.post("/register", json={"email": "bob@e2e.com", "password": "password456"})
        assert r.status_code == 201

        # 3. Login Alice
        r = client.post("/login", json={"email": "alice@e2e.com", "password": "password123"})
        assert r.status_code == 200
        alice_token = r.json()["access_token"]
        ah = auth_header(alice_token)

        # 4. Login Bob
        r = client.post("/login", json={"email": "bob@e2e.com", "password": "password456"})
        bob_token = r.json()["access_token"]
        bh = auth_header(bob_token)

        # 5. Alice creates a note
        r = client.post("/notes", json={"title": "Project Plan", "content": "Phase 1: Setup"}, headers=ah)
        assert r.status_code == 201
        note_id = r.json()["id"]

        # 6. Alice updates the note (creates history v1)
        r = client.put(f"/notes/{note_id}", json={"title": "Project Plan v2", "content": "Phase 2: Build"}, headers=ah)
        assert r.status_code == 200

        # 7. Verify history
        r = client.get(f"/notes/{note_id}/history", headers=ah)
        assert len(r.json()) == 1
        assert r.json()[0]["title"] == "Project Plan"

        # 8. Share with Bob
        r = client.post(f"/notes/{note_id}/share", json={"share_with_email": "bob@e2e.com"}, headers=ah)
        assert r.status_code == 200

        # 9. Bob can read the note
        r = client.get(f"/notes/{note_id}", headers=bh)
        assert r.status_code == 200
        assert r.json()["title"] == "Project Plan v2"

        # 10. Bob CANNOT update it
        r = client.put(f"/notes/{note_id}", json={"title": "Hacked"}, headers=bh)
        assert r.status_code == 403

        # 11. Bob CANNOT delete it
        r = client.delete(f"/notes/{note_id}", headers=bh)
        assert r.status_code == 403

        # 12. Search works for Alice
        r = client.get("/search?q=Phase", headers=ah)
        assert len(r.json()) >= 1

        # 13. Search works for Bob (shared note)
        r = client.get("/search?q=Phase", headers=bh)
        assert len(r.json()) >= 1

        # 14. Alice deletes the note
        r = client.delete(f"/notes/{note_id}", headers=ah)
        assert r.status_code == 204

        # 15. Note is gone
        r = client.get(f"/notes/{note_id}", headers=ah)
        assert r.status_code == 404
