"""SupportPilot tests: auth, isolation, AI triage, drafts, KB, billing caps, analytics."""
import uuid

INTENTS = {"order_status", "shipping", "refund", "complaint", "account", "product_question", "other"}


def _signup(client, role_email=None):
    suffix = uuid.uuid4().hex[:8]
    email = role_email or f"owner-{suffix}@test.store"
    r = client.post("/auth/signup", json={"name": "Owner", "email": email, "password": "owner123", "workspace_name": f"WS {suffix}"})
    assert r.status_code == 200, r.text
    return r.json()


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _make_ticket(client, headers, subject="Where is my order #ORD-4821?", body="Hi, where is my order #ORD-4821? It was placed 5 days ago."):
    r = client.post("/tickets", json={"subject": subject, "body": body, "customer_name": "Test Customer", "customer_email": "c@example.com", "customer_country": "United States", "channel": "email"}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_api_root(client):
    r = client.get("/api")
    assert r.status_code == 200
    assert r.json()["service"] == "SupportPilot API"


def test_landing_is_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "SupportPilot" in r.text
    assert "<html" in r.text.lower()


def test_dashboard_is_html(client):
    r = client.get("/app")
    assert r.status_code == 200
    assert "Inbox" in r.text


def test_signup_and_me(client, auth_headers):
    headers, user, _token = auth_headers
    assert user["role"] == "owner"
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == user["email"]


def test_json_login_200(client, auth_headers):
    _headers_, user, _token = auth_headers
    r = client.post("/auth/login", json={"email": user["email"], "password": "owner123"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_form_login_200_and_token_works(client, auth_headers):
    _h, user, _t = auth_headers
    r = client.post("/auth/login-form", data={"username": user["email"], "password": "owner123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    r2 = client.get("/tickets", headers=_headers(token))
    assert r2.status_code == 200


def test_wrong_password_401(client, auth_headers):
    _h, user, _t = auth_headers
    r = client.post("/auth/login", json={"email": user["email"], "password": "wrongpass"})
    assert r.status_code == 401


def test_ticket_create_auto_triage(client, auth_headers):
    headers, _u, _t = auth_headers
    t = _make_ticket(client, headers)
    assert t["ai_intent"] in INTENTS
    assert t["ai_sentiment"] in {"positive", "neutral", "negative"}
    assert t["ai_priority"] in {"low", "normal", "high", "urgent"}
    assert t["sla_hours"] == 24  # Free plan SLA
    assert t["number"].startswith("SP-")
    # Auto-created AI draft exists
    detail = client.get(f"/tickets/{t['id']}", headers=headers).json()
    assert len(detail["drafts"]) >= 1
    assert detail["drafts"][0]["status"] == "drafted"


def test_workspace_isolation(client, auth_headers):
    headers_a, _u, _t = auth_headers
    ticket = _make_ticket(client, headers_a)
    other = _signup(client)
    r = client.get(f"/tickets/{ticket['id']}", headers=_headers(other["access_token"]))
    assert r.status_code == 404
    r2 = client.get("/tickets", headers=_headers(other["access_token"]))
    assert r2.status_code == 200
    assert all(x["id"] != ticket["id"] for x in r2.json()["tickets"])


def test_draft_approve_then_send(client, auth_headers):
    headers, _u, _t = auth_headers
    ticket = _make_ticket(client, headers)
    detail = client.get(f"/tickets/{ticket['id']}", headers=headers).json()
    draft_id = detail["drafts"][0]["id"]
    r = client.patch(f"/tickets/drafts/{draft_id}", json={"status": "approved"}, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "approved"
    r = client.patch(f"/tickets/drafts/{draft_id}", json={"status": "sent"}, headers=headers)
    assert r.status_code == 200 and r.json()["status"] == "sent"
    detail = client.get(f"/tickets/{ticket['id']}", headers=headers).json()
    assert len(detail["replies"]) >= 1  # sent draft lands on the thread


def test_kb_suggest(client, auth_headers):
    headers, _u, _t = auth_headers
    r = client.post("/kb", json={"title": "How to track your order", "body": "Once your order ships you receive a tracking link by email. Tracking updates can take up to 24 hours to appear after dispatch.", "category": "Shipping"}, headers=headers)
    assert r.status_code == 201, r.text
    ticket = _make_ticket(client, headers, subject="Where is my order?", body="Where is my order? The tracking page has not moved since Monday.")
    r = client.get(f"/tickets/{ticket['id']}/suggest-kb", headers=headers)
    assert r.status_code == 200
    titles = [s["title"] for s in r.json()["suggestions"]]
    assert "How to track your order" in titles


def test_free_plan_cap_then_mock_upgrade_lifts_it(client, auth_headers):
    headers, _u, _t = auth_headers
    for i in range(50):
        r = client.post("/tickets", json={"subject": f"Cap test {i}", "body": "Hello, I have a question about my order.", "customer_name": "C", "channel": "email"}, headers=headers)
        assert r.status_code == 201, r.text
    r = client.post("/tickets", json={"subject": "One too many", "body": "Hello.", "customer_name": "C", "channel": "email"}, headers=headers)
    assert r.status_code == 402  # Free cap enforced
    assert "limit" in r.text.lower()
    r = client.post("/billing/checkout", json={"plan": "pro"}, headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["reference"].startswith("MOCK-STRIPE-")
    r = client.post("/tickets", json={"subject": "After upgrade", "body": "Hello.", "customer_name": "C", "channel": "email"}, headers=headers)
    assert r.status_code == 201  # cap lifted


def test_invite_agent_blocked_on_free_plan(client, auth_headers):
    headers, _u, _t = auth_headers
    r = client.post("/auth/invite", json={"name": "Agent Two", "email": f"agent-{uuid.uuid4().hex[:8]}@test.store", "password": "agent123", "role": "agent"}, headers=headers)
    assert r.status_code == 402  # Free allows only 1 agent (the owner)


def test_resolve_with_csat_and_reply_sets_first_response(client, auth_headers):
    headers, _u, _t = auth_headers
    ticket = _make_ticket(client, headers)
    r = client.post(f"/tickets/{ticket['id']}/replies", json={"body": "Looking into it now."}, headers=headers)
    assert r.status_code == 201
    r = client.post(f"/tickets/{ticket['id']}/resolve", json={"csat_rating": 5}, headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "resolved"
    assert r.json()["csat_rating"] == 5


def test_analytics_summary(client, auth_headers):
    headers, _u, _t = auth_headers
    _make_ticket(client, headers)
    r = client.get("/analytics/summary", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_tickets"] >= 1
    assert "by_status" in data and "by_intent" in data and "by_channel" in data
    assert "resolution_rate" in data


def test_billing_status_free(client, auth_headers):
    headers, _u, _t = auth_headers
    r = client.get("/billing", headers=headers)
    assert r.status_code == 200
    assert r.json()["plan"] == "free"
    assert r.json()["mock"] is True
