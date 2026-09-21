"""Unit and integration tests for authentication, JWT security, and user favorites."""

import uuid
from datetime import timedelta
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import settings
from app.db.models import Base, User, UserFavorite
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.main import app
import app.auth.security as auth_sec
import app.auth.router as auth_rt


# Use an in-memory SQLite async engine for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
def patch_db_sessions(monkeypatch):
    """Patch AsyncSessionLocal in auth modules to use in-memory SQLite."""
    monkeypatch.setattr(auth_sec, "AsyncSessionLocal", TestSessionLocal)
    monkeypatch.setattr(auth_rt, "AsyncSessionLocal", TestSessionLocal)


@pytest_asyncio.fixture(autouse=True)
async def init_test_db():
    """Create auth tables in memory before each test and drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                sync_conn, tables=[User.__table__, UserFavorite.__table__]
            )
        )
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(
                sync_conn, tables=[UserFavorite.__table__, User.__table__]
            )
        )


@pytest.fixture
def client():
    return TestClient(app)


# --- Unit Tests: Security ---

def test_password_hashing_and_verification():
    raw_pwd = "SuperSecretPassword123!"
    hashed = hash_password(raw_pwd)

    assert hashed != raw_pwd
    assert hashed.startswith("$2b$")
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_token_generation_and_decoding():
    user_id = str(uuid.uuid4())
    email = "agent@nivaas.in"
    token = create_access_token({"sub": user_id, "email": email})

    assert isinstance(token, str)
    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == user_id
    assert claims["email"] == email
    assert "exp" in claims
    assert "iat" in claims


def test_jwt_token_expired():
    user_id = str(uuid.uuid4())
    token = create_access_token(
        {"sub": user_id, "email": "expired@nivaas.in"},
        expires_delta=timedelta(seconds=-10),
    )
    claims = decode_access_token(token)
    assert claims is None


def test_jwt_token_tampered():
    token = create_access_token({"sub": "123", "email": "tamper@nivaas.in"})
    tampered = token[:-4] + "fake"
    claims = decode_access_token(tampered)
    assert claims is None


# --- Integration Tests: Auth Endpoints ---

def test_user_registration_success(client):
    res = client.post(
        "/api/auth/register",
        json={
            "email": "riya.sharma@example.com",
            "password": "Password@2026",
            "full_name": "Riya Sharma",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert data["user"]["email"] == "riya.sharma@example.com"
    assert data["user"]["full_name"] == "Riya Sharma"
    assert "access_token" in res.cookies


def test_user_registration_duplicate_email(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password@2026",
        "full_name": "Duplicate Test",
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 200

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"].lower()


def test_user_registration_short_password(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "short@example.com", "password": "123"},
    )
    assert res.status_code == 422


def test_user_login_success_and_logout(client):
    # 1. Register user
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "ValidPassword123!"},
    )

    # 2. Login
    res = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "ValidPassword123!"},
    )
    assert res.status_code == 200
    token = res.json()["token"]
    assert token is not None

    # 3. Access protected /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "login@example.com"

    # 4. Logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200


def test_user_login_invalid_credentials(client):
    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "WrongPassword123!"},
    )
    assert res.status_code == 401


def test_unauthenticated_access_denied(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_user_favorites_flow(client):
    # Register & get auth token
    reg_res = client.post(
        "/api/auth/register",
        json={"email": "favorites@example.com", "password": "Password@2026"},
    )
    token = reg_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Initially empty favorites
    list_res = client.get("/api/user/favorites", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json() == []

    # 2. Add a favorite property
    fav_payload = {
        "listing_id": "prop-101",
        "title": "Luxury 3 BHK in Whitefield",
        "locality": "Whitefield",
        "city": "Bengaluru",
        "price_inr": 18500000,
        "bhk": 3,
        "source_url": "https://example.com/prop-101",
        "metadata_json": {"carpet_area_sqft": 1650},
    }
    add_res = client.post("/api/user/favorites", json=fav_payload, headers=headers)
    assert add_res.status_code == 200
    fav_data = add_res.json()
    fav_id = fav_data["id"]
    assert fav_data["title"] == "Luxury 3 BHK in Whitefield"

    # 3. Verify in list
    list_res2 = client.get("/api/user/favorites", headers=headers)
    assert list_res2.status_code == 200
    items = list_res2.json()
    assert len(items) == 1
    assert items[0]["id"] == fav_id

    # 4. Delete favorite
    del_res = client.delete(f"/api/user/favorites/{fav_id}", headers=headers)
    assert del_res.status_code == 200

    # 5. Verify deleted
    list_res3 = client.get("/api/user/favorites", headers=headers)
    assert list_res3.status_code == 200
    assert list_res3.json() == []
