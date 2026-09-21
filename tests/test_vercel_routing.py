"""Tests for Vercel serverless routing, rewrite headers, and 405 prevention."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.agent.loop import AgentState


@pytest.fixture
def client():
    return TestClient(app)


def test_cors_options_preflight(client):
    """Ensure OPTIONS preflight requests are accepted with 200 OK."""
    res = client.options(
        "/api/chat",
        headers={
            "Origin": "https://nivaas.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers


@patch("app.main.run_agent", new_callable=AsyncMock)
def test_direct_api_chat(mock_run_agent, client):
    """Ensure direct POST /api/chat works."""
    mock_run_agent.return_value = ("Found 1 property", AgentState())
    res = client.post("/api/chat", json={"message": "2 BHK Pune"})
    assert res.status_code == 200
    data = res.json()
    assert data["response"] == "Found 1 property"


@patch("app.main.run_agent", new_callable=AsyncMock)
def test_vercel_rewrite_with_matched_path_header(mock_run_agent, client):
    """When Vercel rewrites to /api/index.py, x-matched-path header restores the route."""
    mock_run_agent.return_value = ("Matched path restored", AgentState())
    res = client.post(
        "/api/index.py",
        headers={"x-matched-path": "/api/chat"},
        json={"message": "3 BHK Bangalore"},
    )
    assert res.status_code == 200
    assert res.json()["response"] == "Matched path restored"


@patch("app.main.run_agent", new_callable=AsyncMock)
def test_vercel_rewrite_with_forwarded_uri_header(mock_run_agent, client):
    """When Vercel rewrites to /api/index.py, x-forwarded-uri header restores the route."""
    mock_run_agent.return_value = ("Forwarded URI restored", AgentState())
    res = client.post(
        "/api/index.py",
        headers={"x-forwarded-uri": "/api/chat"},
        json={"message": "Penthouse Mumbai"},
    )
    assert res.status_code == 200
    assert res.json()["response"] == "Forwarded URI restored"


@patch("app.main.run_agent", new_callable=AsyncMock)
def test_vercel_fallback_post_without_headers(mock_run_agent, client):
    """If no rewrite headers are present and a POST arrives at /api/index.py, never return 405."""
    mock_run_agent.return_value = ("Fallback succeeded", AgentState())
    res = client.post(
        "/api/index.py",
        json={"message": "Villa Gurgaon"},
    )
    assert res.status_code == 200
    assert res.json()["response"] == "Fallback succeeded"


def test_fallback_post_emi_without_headers(client):
    """EMI calculations via serverless fallback root endpoint."""
    res = client.post(
        "/api/index.py",
        json={"price_inr": 5000000, "down_payment_pct": 20, "annual_rate": 8.5, "tenure_years": 20},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["emi"] > 0
    assert data["total_payable"] > 0


def test_fallback_post_emi_with_alternative_keys(client):
    """EMI calculations supporting alternative key names (property_price, annual_interest_rate)."""
    res = client.post(
        "/api/index.py",
        json={"property_price": 6000000, "down_payment_pct": 25, "annual_interest_rate": 8.75, "tenure_years": 15},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["emi"] > 0


@patch("app.main.run_agent", new_callable=AsyncMock)
def test_mixed_case_matched_path_header(mock_run_agent, client):
    """Test mixed-case X-Matched-Path header works properly."""
    mock_run_agent.return_value = ("Mixed case works", AgentState())
    res = client.post(
        "/api/index.py",
        headers={"X-Matched-Path": "/api/chat"},
        json={"message": "1 BHK Pune"},
    )
    assert res.status_code == 200
    assert res.json()["response"] == "Mixed case works"


def test_get_page_routes(client):
    """Ensure HTML pages load properly across various Vercel aliases."""
    for path in ["/", "/api", "/api/index.py", "/index.html"]:
        res = client.get(path)
        assert res.status_code == 200
        assert "text/html" in res.headers.get("content-type", "")


def test_fallback_post_auth_registration(client):
    """Ensure POST to /api/index.py with auth payload successfully routes to registration."""
    import uuid
    unique_email = f"vercel_{uuid.uuid4().hex[:8]}@example.com"
    res = client.post(
        "/api/index.py?action=register",
        json={
            "email": unique_email,
            "password": "Password@2026",
            "full_name": "Vercel Test User",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == unique_email
