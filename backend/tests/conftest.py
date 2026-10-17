from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import pymongo
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.db.mongo import get_mongo
from app.main import app
from app.models.admin import Role
from app.modules.admins.service import create_admin as admins_create_admin
from app.services.email import reset_email_transport
from app.services.rate_limit import login_rate_limiter, onboarding_rate_limiter
from app.storage import get_storage_provider

# ---------------------------------------------------------------------------
# Isolation: tests NEVER touch the real database, the real JWT secret or real
# storage. A dedicated database and a dedicated local storage directory are
# used, and both are removed when the session finishes.
# ---------------------------------------------------------------------------
TEST_DB_NAME = "thridha_labs_test"
TEST_JWT_SECRET = "phase2-test-only-jwt-secret-not-for-production-00000000"
TEST_STORAGE_DIR = os.path.join(os.environ.get("TEMP", "/tmp"), "thridha_labs_test_storage")
# A real, non-localhost origin so certificate QR/verification URLs are always
# buildable in tests (localhost is intentionally rejected by the service).
TEST_CERTIFICATE_BASE_URL = "https://thridhalabs.test"
# Dedicated AI settings encryption key (never the JWT secret).
TEST_AI_ENCRYPTION_KEY = "test-only-ai-settings-encryption-key-0123456789abcdef"
_OVERRIDDEN_KEYS = (
    "MONGO_DB_NAME",
    "JWT_SECRET",
    "STORAGE_MODE",
    "STORAGE_LOCAL_DIR",
    "EMAIL_MOCK",
    "CERTIFICATE_VERIFY_BASE_URL",
    "AI_SETTINGS_ENCRYPTION_KEY",
)


def _reset_storage() -> None:
    """Wipe the configured local storage directory and the provider cache."""
    root = Path(get_settings().STORAGE_LOCAL_DIR)
    if root.exists():
        shutil.rmtree(root)
    get_storage_provider.cache_clear()


@pytest.fixture(scope="session", autouse=True)
def isolated_test_environment():
    previous = {key: os.environ.get(key) for key in _OVERRIDDEN_KEYS}
    os.environ["MONGO_DB_NAME"] = TEST_DB_NAME
    os.environ["JWT_SECRET"] = TEST_JWT_SECRET
    os.environ["STORAGE_MODE"] = "local"
    os.environ["STORAGE_LOCAL_DIR"] = TEST_STORAGE_DIR
    # Never send real mail from tests: force the log-only email transport.
    os.environ["EMAIL_MOCK"] = "true"
    os.environ["CERTIFICATE_VERIFY_BASE_URL"] = TEST_CERTIFICATE_BASE_URL
    os.environ["AI_SETTINGS_ENCRYPTION_KEY"] = TEST_AI_ENCRYPTION_KEY
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    reset_email_transport()
    assert get_settings().MONGO_DB_NAME == TEST_DB_NAME
    assert get_settings().STORAGE_MODE == "local"
    assert get_settings().EMAIL_MOCK is True
    assert get_settings().verification_base_url == TEST_CERTIFICATE_BASE_URL
    assert get_settings().ai_encryption_configured is True

    yield

    settings = get_settings()
    assert settings.MONGO_DB_NAME == TEST_DB_NAME, "refusing to drop an unexpected database"
    drop_client = pymongo.MongoClient(
        settings.MONGO_URI.get_secret_value(), serverSelectionTimeoutMS=5000
    )
    try:
        drop_client.drop_database(TEST_DB_NAME)
    finally:
        drop_client.close()

    if Path(TEST_STORAGE_DIR).exists():
        shutil.rmtree(TEST_STORAGE_DIR, ignore_errors=True)

    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    get_settings.cache_clear()
    get_storage_provider.cache_clear()
    reset_email_transport()


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    login_rate_limiter.clear()
    onboarding_rate_limiter.clear()
    yield
    login_rate_limiter.clear()
    onboarding_rate_limiter.clear()


@pytest.fixture
async def client():
    """ASGI test client over a TLS base URL so the production cookie policy
    (Secure + SameSite=None) behaves exactly as it does in production.

    Also gives every test a clean `admins` and `media` collection and a clean
    local storage directory before it runs.
    """
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="https://testserver"
        ) as ac:
            db = get_mongo().database
            for collection in (
                "admins", "media", "settings", "branding",
                "clients", "projects", "testimonials",
                "careers_settings", "careers_opportunities",
                "members", "members_counters",
                "member_works", "certification_requests",
                "certificates",
                "activities", "activity_participations",
                "progress_reports",
                "ai_settings", "ai_summaries",
            ):
                await db[collection].delete_many({})
            _reset_storage()
            yield ac
            _reset_storage()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def make_admin(client):
    async def _make(
        email: str,
        password: str = "CorrectHorse!Battery9",
        role: Role = Role.OWNER,
        is_active: bool = True,
    ):
        return await admins_create_admin(email, password, role, is_active=is_active)

    return _make


@pytest.fixture
def fetch_csrf(client):
    async def _fetch() -> str:
        res = await client.get("/api/auth/csrf")
        assert res.status_code == 200, res.text
        return res.json()["csrfToken"]

    return _fetch


@pytest.fixture
async def csrf_token(fetch_csrf):
    return await fetch_csrf()


@pytest.fixture
def login(client, csrf_token):
    async def _login(email: str, password: str):
        return await client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
            headers={"X-CSRF-Token": csrf_token},
        )

    return _login


@pytest.fixture
def logout(client, fetch_csrf):
    async def _logout():
        token = await fetch_csrf()
        return await client.post(
            "/api/auth/logout", headers={"X-CSRF-Token": token}
        )

    return _logout
