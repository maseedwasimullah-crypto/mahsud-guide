"""API-level smoke tests: health, retrieval, assistant, auth and RBAC."""

from __future__ import annotations


def test_health_reports_configuration(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["llm_provider"] == "none"
    assert payload["embedding_provider"] == "local"
    assert payload["counts"]["documents"] >= 1


def test_overview_lists_knowledge_base_counts(client):
    payload = client.get("/api/assistant/overview").json()
    assert payload["counts"]["documents"] >= 1
    assert payload["counts"]["chunks"] >= 1
    assert payload["llm"]["configured"] is False


def test_search_returns_cited_hits(client):
    hits = client.post("/api/search", json={"query": "MDCAT 50 percent weight aggregate", "limit": 5}).json()
    assert hits, "expected at least one retrieval hit"
    top = hits[0]
    assert top["url"]
    assert top["verification_status"] == "verified"
    assert "MDCAT" in top["excerpt"] or "aggregate" in top["excerpt"].lower()


def test_chat_is_grounded_and_cites_a_source(client):
    payload = client.post(
        "/api/assistant/chat",
        json={"message": "What is the aggregate formula for MBBS in KP?", "program": "MBBS"},
    ).json()
    assert payload["answer"]
    assert payload["citations"], "answers must cite the documents they came from"
    assert any("kmu.edu.pk" in (c.get("url") or "") or "example.test" in (c.get("url") or "") for c in payload["citations"])
    assert "is_admission_decision" not in payload["answer"].lower()


def test_aggregate_calculate_via_api(client):
    formulas = client.get("/api/aggregate/formulas", params={"program": "MBBS"}).json()
    usable = [f for f in formulas if f["usable"]]
    assert usable, "expected a usable MBBS formula"
    response = client.post(
        "/api/aggregate/calculate",
        json={"formula_id": usable[0]["id"], "inputs": {"ssc": 80, "hssc": 80, "mdcat": 60}},
    )
    assert response.status_code == 200
    assert response.json()["aggregate"] == 70.0


def test_aggregate_pending_formula_is_refused_via_api(client):
    formulas = client.get("/api/aggregate/formulas").json()
    pending = [f for f in formulas if not f["usable"]]
    assert pending, "expected a pending formula in the knowledge base"
    response = client.post(
        "/api/aggregate/calculate",
        json={"formula_id": pending[0]["id"], "inputs": {"ssc": 80}},
    )
    assert response.status_code == 422
    assert "verified" in response.json()["detail"].lower()


def test_aggregate_unknown_formula_404(client):
    response = client.post("/api/aggregate/calculate", json={"formula_id": 999999, "inputs": {}})
    assert response.status_code == 404


def test_eligibility_via_api(client):
    response = client.post(
        "/api/eligibility/check",
        json={"program": "MBBS", "hssc_percent": 85, "mdcat_percent": 70, "subjects": ["Biology", "Chemistry", "Physics"]},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "eligible"
    assert response.json()["is_admission_decision"] is False


def test_login_and_admin_stats(client):
    bad = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "wrong-password"})
    assert bad.status_code == 401

    ok = client.post("/api/auth/login", json={"email": "admin@test.local", "password": "correct-horse-battery-staple"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    assert ok.json()["role"] == "admin"

    stats = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert stats.status_code == 200
    assert stats.json()["documents"] >= 1


def test_admin_endpoints_require_authentication(client):
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/admin/sources", json={"name": "x", "url": "https://x.test"}).status_code == 401


def test_nonexistent_token_is_rejected(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
