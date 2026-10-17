"""Groq AI work-summarization tests.

Covers the admin-only, CSRF-protected AI settings surface (dynamic key storage
with AEAD encryption, masking, replacement, removal and non-disclosure), the
connection test (provider mocked — no real Groq calls), and the summarization
workflow: approved-reports-only generation, draft review, explicit publish,
unpublish, stale-source detection, provider-failure preservation, and the
member-facing contribution history.

NO test ever makes a real network call: `app.modules.ai.groq.chat_completion`
and `app.modules.ai.groq.test_connection` are monkeypatched, and the API key
value used in tests is a fake that never leaves this process.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core import crypto
from app.core.config import get_settings
from app.core.errors import AppError
from app.main import app
from app.models.admin import Role
from app.modules.ai import groq as groq_module
from tests._content_helpers import (
    capture_onboarding_token,
    create_activity,
    create_member,
    invite_to_activity,
    list_activity_participants,
    login_admin,
    member_login,
    member_setup,
    publish_activity,
    update_participant,
)

TEST_KEY = "gsk_test_0123456789abcdefghijklmnopqrstuvwxyz"
TEST_KEY_2 = "gsk_test_zyxwvutsrqponmlkjihgfedcba9876543210"


def _second_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://testserver")


# ---------------------------------------------------------------------------
# Mocking / helpers
# ---------------------------------------------------------------------------
def mock_groq(
    monkeypatch,
    *,
    content: str = "Delivered the analytics dashboard and migrated the pipeline.",
    error: Exception | None = None,
    connection_result: dict | None = None,
    connection_error: Exception | None = None,
) -> dict:
    """Patch the Groq client. Returns a `calls` dict capturing invocations."""
    calls: dict = {"chat": 0, "prompts": [], "connections": 0}

    async def _chat(api_key, *, model, system_prompt, user_prompt, **kwargs):  # noqa: ANN001
        calls["chat"] += 1
        calls["prompts"].append(
            {
                "api_key": api_key,
                "model": model,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
            }
        )
        if error is not None:
            raise error
        return content

    async def _test(api_key, model):  # noqa: ANN001
        calls["connections"] += 1
        if connection_error is not None:
            raise connection_error
        return connection_result or {
            "models_available": 12,
            "model_available": True,
            "latency_ms": 42,
        }

    monkeypatch.setattr(groq_module, "chat_completion", _chat)
    monkeypatch.setattr(groq_module, "test_connection", _test)
    return calls


async def _configure_key(client, token: str, key: str = TEST_KEY) -> None:
    res = await client.put(
        "/api/admin/ai/settings",
        json={"api_key": key},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text


async def _confirmed_member(
    client,
    admin_token: str,
    monkeypatch,
    *,
    email: str,
    title: str = "AI Project",
):
    """Create a member + published project and confirm the member's participation.

    Returns (member_client, member_csrf, project, member, readable_id).
    """
    capture = capture_onboarding_token(monkeypatch)
    member = await create_member(
        client, admin_token, email=email, full_name=email.split("@")[0]
    )
    project = await create_activity(
        client, admin_token, title=title, activity_type="project"
    )
    await publish_activity(client, admin_token, project["id"])

    member_client = _second_client()
    await member_setup(member_client, capture["token"])
    mtoken = await member_login(member_client, email)
    readable = member["member_id"]
    status, _ = await invite_to_activity(
        client, admin_token, project["id"], [{"member_id": member["id"]}]
    )
    assert status == 200
    participants = await list_activity_participants(
        client, admin_token, project["id"]
    )
    p = next(
        item for item in participants["items"] if item["member_readable_id"] == readable
    )
    _, body = await update_participant(
        client, admin_token, project["id"], p["id"], status="confirmed"
    )
    assert body["status"] == "confirmed"
    return member_client, mtoken, project, member, readable


async def _submit(member_client, token, project_id, description: str) -> dict:
    res = await member_client.post(
        "/api/member/reports",
        json={"activity_id": project_id, "description": description},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _approve(client, admin_token, report_id: str) -> dict:
    res = await client.post(
        f"/api/admin/reports/{report_id}/decision",
        json={"action": "approve"},
        headers={"X-CSRF-Token": admin_token},
    )
    assert res.status_code == 200, res.text
    return res.json()


async def _generate(client, token, activity_id, member_id):
    return await client.post(
        "/api/admin/ai/summaries/generate",
        json={"activity_id": activity_id, "member_id": member_id},
        headers={"X-CSRF-Token": token},
    )


# ---------------------------------------------------------------------------
# Settings: auth / RBAC / CSRF
# ---------------------------------------------------------------------------
async def test_ai_settings_requires_authentication(client):
    res = await client.get("/api/admin/ai/settings")
    assert res.status_code == 401, res.text


async def test_ai_settings_requires_admin_role(client, make_admin, fetch_csrf):
    editor_token = await login_admin(
        client, make_admin, fetch_csrf, email="editor-ai@example.com", role=Role.EDITOR
    )
    res = await client.get(
        "/api/admin/ai/settings", headers={"X-CSRF-Token": editor_token}
    )
    assert res.status_code == 403, res.text

    res = await client.put(
        "/api/admin/ai/settings",
        json={"api_key": TEST_KEY},
        headers={"X-CSRF-Token": editor_token},
    )
    assert res.status_code == 403, res.text


async def test_ai_settings_put_requires_csrf(client, make_admin, fetch_csrf):
    await login_admin(client, make_admin, fetch_csrf, email="owner-ai-csrf@example.com")
    res = await client.put("/api/admin/ai/settings", json={"api_key": TEST_KEY})
    assert res.status_code == 403, res.text


async def test_member_cannot_reach_ai_admin(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf)
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="member-ai@example.com"
    )
    try:
        res = await member_client.get(
            "/api/admin/ai/settings", headers={"X-CSRF-Token": mtoken}
        )
        assert res.status_code in (401, 403), res.text
        _s = await _submit(member_client, mtoken, project["id"], "did work")
        _ = _s
        res = await member_client.post(
            "/api/admin/ai/summaries/generate",
            json={"activity_id": project["id"], "member_id": member["id"]},
            headers={"X-CSRF-Token": mtoken},
        )
        assert res.status_code in (401, 403), res.text
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Settings: encryption, masking, replacement, removal, non-disclosure
# ---------------------------------------------------------------------------
async def test_connection_requires_authentication(client, fetch_csrf):
    res = await client.post("/api/admin/ai/settings/test", json={})
    assert res.status_code in (401, 403), res.text


async def test_store_key_encrypts_masks_and_never_discloses(
    client, make_admin, fetch_csrf
):
    token = await login_admin(client, make_admin, fetch_csrf, email="owner-store@example.com")

    res = await client.get("/api/admin/ai/settings")
    assert res.status_code == 200
    initial = res.json()
    assert initial["configured"] is False
    assert initial["encryption_available"] is True
    assert initial["key_hint"] is None

    await _configure_key(client, token, TEST_KEY)

    res = await client.get("/api/admin/ai/settings")
    body = res.json()
    assert body["configured"] is True
    assert body["key_hint"] == "\u2022" * 8 + TEST_KEY[-4:]
    assert body["key_set_at"] is not None
    # The raw key is nowhere in the response.
    assert TEST_KEY not in res.text

    # Persisted only as ciphertext; plaintext never present.
    from app.db.mongo import get_mongo

    doc = await get_mongo().database["ai_settings"].find_one({})
    assert doc is not None
    assert doc["api_key_encrypted"].startswith("v1:")
    assert doc["api_key_encrypted"] != TEST_KEY
    assert TEST_KEY not in str(doc)
    stored_ciphertext = doc["api_key_encrypted"]

    # Replace: ciphertext + hint change, still encrypted.
    await _configure_key(client, token, TEST_KEY_2)
    doc2 = await get_mongo().database["ai_settings"].find_one({})
    assert doc2["api_key_encrypted"] != stored_ciphertext
    res = await client.get("/api/admin/ai/settings")
    assert res.json()["key_hint"] == "\u2022" * 8 + TEST_KEY_2[-4:]
    assert TEST_KEY_2 not in res.text

    # Remove.
    res = await client.delete(
        "/api/admin/ai/settings/key", headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200, res.text
    assert res.json()["configured"] is False
    doc3 = await get_mongo().database["ai_settings"].find_one({})
    assert doc3["api_key_encrypted"] is None


async def test_store_key_refused_without_encryption_key(
    client, make_admin, fetch_csrf, monkeypatch
):
    token = await login_admin(
        client, make_admin, fetch_csrf, email="owner-noenc@example.com"
    )
    monkeypatch.delenv("AI_SETTINGS_ENCRYPTION_KEY", raising=False)
    get_settings.cache_clear()
    try:
        res = await client.put(
            "/api/admin/ai/settings",
            json={"api_key": TEST_KEY},
            headers={"X-CSRF-Token": token},
        )
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "AI_ENCRYPTION_UNAVAILABLE"
        # Nothing was stored in plaintext.
        from app.db.mongo import get_mongo

        doc = await get_mongo().database["ai_settings"].find_one({})
        assert doc is None or doc.get("api_key_encrypted") is None
    finally:
        get_settings.cache_clear()


# ---------------------------------------------------------------------------
# Connection test (mocked)
# ---------------------------------------------------------------------------
async def test_connection_test_success_does_not_persist_proposed_key(
    client, make_admin, fetch_csrf, monkeypatch
):
    token = await login_admin(client, make_admin, fetch_csrf, email="owner-test@example.com")
    mock_groq(monkeypatch, connection_result={"models_available": 9, "model_available": True, "latency_ms": 7})

    res = await client.post(
        "/api/admin/ai/settings/test",
        json={"api_key": TEST_KEY},
        headers={"X-CSRF-Token": token},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is True
    assert body["model_available"] is True

    # A proposed key is never persisted.
    res = await client.get("/api/admin/ai/settings")
    assert res.json()["configured"] is False


async def test_connection_test_failure_is_reported_and_sanitized(
    client, make_admin, fetch_csrf, monkeypatch
):
    token = await login_admin(client, make_admin, fetch_csrf, email="owner-testfail@example.com")
    await _configure_key(client, token)
    mock_groq(
        monkeypatch,
        connection_error=groq_module.GroqError(
            "GROQ_INVALID_KEY", "Groq rejected the API key. Check the key and try again."
        ),
    )
    res = await client.post(
        "/api/admin/ai/settings/test", json={}, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["ok"] is False
    assert body["error_code"] == "GROQ_INVALID_KEY"
    assert TEST_KEY not in res.text

    res = await client.get("/api/admin/ai/settings")
    assert res.json()["last_test_ok"] is False


async def test_connection_test_without_stored_key(client, make_admin, fetch_csrf):
    token = await login_admin(client, make_admin, fetch_csrf, email="owner-testnone@example.com")
    res = await client.post(
        "/api/admin/ai/settings/test", json={}, headers={"X-CSRF-Token": token}
    )
    assert res.status_code == 409, res.text
    assert res.json()["error"]["code"] == "AI_NOT_CONFIGURED"


# ---------------------------------------------------------------------------
# Crypto unit checks
# ---------------------------------------------------------------------------
def test_crypto_round_trip_and_tamper_detection():
    token = crypto.encrypt_secret("hello-secret")
    assert token.startswith("v1:")
    assert crypto.encrypt_secret("hello-secret") != token  # random nonce
    assert crypto.decrypt_secret(token) == "hello-secret"

    tampered = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(AppError):
        crypto.decrypt_secret(tampered)


# ---------------------------------------------------------------------------
# Summarization: authorization
# ---------------------------------------------------------------------------
async def test_generate_requires_admin_and_csrf(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-gen@example.com")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="gen@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Built the API.")
        await _approve(client, admin_token, report["id"])

        # No CSRF.
        res = await client.post(
            "/api/admin/ai/summaries/generate",
            json={"activity_id": project["id"], "member_id": member["id"]},
        )
        assert res.status_code == 403, res.text

        # Editor cannot generate.
        editor_token = await login_admin(
            client, make_admin, fetch_csrf, email="gen-editor@example.com", role=Role.EDITOR
        )
        res = await client.post(
            "/api/admin/ai/summaries/generate",
            json={"activity_id": project["id"], "member_id": member["id"]},
            headers={"X-CSRF-Token": editor_token},
        )
        assert res.status_code == 403, res.text
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Summarization: approved-only + generation
# ---------------------------------------------------------------------------
async def test_generate_uses_only_approved_reports(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-approved@example.com")
    await _configure_key(client, admin_token)
    calls = mock_groq(monkeypatch, content="Summary text.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="approved@example.com"
    )
    try:
        approved = await _submit(member_client, mtoken, project["id"], "Approved work.")
        await _approve(client, admin_token, approved["id"])
        pending = await _submit(member_client, mtoken, project["id"], "Pending work.")

        res = await _generate(client, admin_token, project["id"], member["id"])
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["state"] == "draft"
        assert body["draft_content"] == "Summary text."
        assert body["published_content"] is None
        assert body["source_report_count"] == 1
        assert [s["report_id"] for s in body["source_reports"]] == [approved["id"]]
        assert pending["id"] not in [s["report_id"] for s in body["source_reports"]]

        # The pending report text is not in the prompt sent to the provider.
        prompt = calls["prompts"][0]["user_prompt"]
        assert "Approved work." in prompt
        assert "Pending work." not in prompt
        # The API key is sent to the provider as auth but never in the prompt.
        assert calls["prompts"][0]["api_key"] == TEST_KEY
        assert TEST_KEY not in prompt
    finally:
        await member_client.aclose()


async def test_generate_without_approved_reports_conflicts(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-none@example.com")
    await _configure_key(client, admin_token)
    mock_groq(monkeypatch)
    member_client, _mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="none@example.com"
    )
    try:
        res = await _generate(client, admin_token, project["id"], member["id"])
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "AI_NO_APPROVED_REPORTS"
    finally:
        await member_client.aclose()


async def test_generate_requires_configured_key(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-nokey@example.com")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="nokey@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work done.")
        await _approve(client, admin_token, report["id"])
        res = await _generate(client, admin_token, project["id"], member["id"])
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "AI_NOT_CONFIGURED"
    finally:
        await member_client.aclose()


async def test_unchanged_sources_do_not_call_provider_twice(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-dup@example.com")
    await _configure_key(client, admin_token)
    calls = mock_groq(monkeypatch, content="Stable summary.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="dup@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work.")
        await _approve(client, admin_token, report["id"])

        first = await _generate(client, admin_token, project["id"], member["id"])
        assert first.status_code == 200
        second = await _generate(client, admin_token, project["id"], member["id"])
        assert second.status_code == 200
        assert calls["chat"] == 1  # double-click does not re-call the provider
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Review / publish / unpublish
# ---------------------------------------------------------------------------
async def test_publish_requires_reviewed_draft(client, make_admin, fetch_csrf, monkeypatch):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-rev@example.com")
    await _configure_key(client, admin_token)
    mock_groq(monkeypatch, content="Generated summary.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="rev@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work.")
        await _approve(client, admin_token, report["id"])
        gen = await _generate(client, admin_token, project["id"], member["id"])
        summary_id = gen.json()["id"]

        # Publishing before review/save is refused.
        res = await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "AI_DRAFT_NOT_REVIEWED"

        # Save (review) with edited content.
        res = await client.patch(
            f"/api/admin/ai/summaries/{summary_id}",
            json={"draft_content": "Edited and reviewed summary."},
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["draft_reviewed"] is True

        # Publish explicitly.
        res = await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["state"] == "published"
        assert body["published_content"] == "Edited and reviewed summary."
        assert body["draft_content"] is None
    finally:
        await member_client.aclose()


async def test_published_summary_appears_in_member_history(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-hist@example.com")
    await _configure_key(client, admin_token)
    mock_groq(monkeypatch, content="Generated.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="hist@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work.")
        await _approve(client, admin_token, report["id"])
        gen = await _generate(client, admin_token, project["id"], member["id"])
        summary_id = gen.json()["id"]

        # Not visible to the member before publishing.
        hist = await member_client.get("/api/member/reports/contributions")
        assert hist.status_code == 200, hist.text
        assert all(not group["summaries"] for group in hist.json()["items"])

        await client.patch(
            f"/api/admin/ai/summaries/{summary_id}",
            json={"draft_content": "Final reviewed summary."},
            headers={"X-CSRF-Token": admin_token},
        )
        await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )

        hist = await member_client.get("/api/member/reports/contributions")
        groups = [g for g in hist.json()["items"] if g["activity_id"] == project["id"]]
        assert groups, hist.text
        summaries = groups[0]["summaries"]
        assert len(summaries) == 1
        assert summaries[0]["content"] == "Final reviewed summary."
        assert summaries[0]["source_report_ids"] == [report["id"]]
        # The underlying approved report remains listed as evidence.
        assert any(r["id"] == report["id"] for r in groups[0]["reports"])

        # Unpublish removes it from official history (returned to a draft).
        res = await client.post(
            f"/api/admin/ai/summaries/{summary_id}/unpublish",
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["state"] == "draft"
        hist = await member_client.get("/api/member/reports/contributions")
        groups = [g for g in hist.json()["items"] if g["activity_id"] == project["id"]]
        assert all(not g["summaries"] for g in groups)
    finally:
        await member_client.aclose()


async def test_stale_sources_block_publish_until_regenerated(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-stale@example.com")
    await _configure_key(client, admin_token)
    mock_groq(monkeypatch, content="Version one.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="stale@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "First work.")
        await _approve(client, admin_token, report["id"])
        gen = await _generate(client, admin_token, project["id"], member["id"])
        summary_id = gen.json()["id"]
        await client.patch(
            f"/api/admin/ai/summaries/{summary_id}",
            json={"draft_content": "Reviewed v1."},
            headers={"X-CSRF-Token": admin_token},
        )

        # A new approved report changes the source hash.
        second = await _submit(member_client, mtoken, project["id"], "Second work.")
        await _approve(client, admin_token, second["id"])

        # The reviewed draft is now stale: publishing is refused.
        res = await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 409, res.text
        assert res.json()["error"]["code"] == "AI_DRAFT_OUTDATED"

        # Regenerate (now includes both reports), review and publish.
        regen = await _generate(client, admin_token, project["id"], member["id"])
        assert regen.status_code == 200, regen.text
        assert regen.json()["source_report_count"] == 2
        await client.patch(
            f"/api/admin/ai/summaries/{summary_id}",
            json={"draft_content": "Reviewed v2."},
            headers={"X-CSRF-Token": admin_token},
        )
        res = await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )
        assert res.status_code == 200, res.text
        assert res.json()["state"] == "published"
    finally:
        await member_client.aclose()


async def test_generation_failure_preserves_published_summary(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-fail@example.com")
    await _configure_key(client, admin_token)
    mock_groq(monkeypatch, content="Published content.")
    member_client, mtoken, project, member, _readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="fail@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work.")
        await _approve(client, admin_token, report["id"])
        gen = await _generate(client, admin_token, project["id"], member["id"])
        summary_id = gen.json()["id"]
        await client.patch(
            f"/api/admin/ai/summaries/{summary_id}",
            json={"draft_content": "Reviewed publish."},
            headers={"X-CSRF-Token": admin_token},
        )
        await client.post(
            f"/api/admin/ai/summaries/{summary_id}/publish",
            headers={"X-CSRF-Token": admin_token},
        )

        # Now the provider fails on the next generation attempt.
        async def _failing_chat(*args, **kwargs):  # noqa: ANN002, ANN003
            raise groq_module.GroqError(
                "GROQ_UNAVAILABLE", "Groq is temporarily unavailable."
            )

        monkeypatch.setattr(groq_module, "chat_completion", _failing_chat)
        # A new approved report makes the sources differ so generation proceeds.
        second = await _submit(member_client, mtoken, project["id"], "More work.")
        await _approve(client, admin_token, second["id"])

        res = await _generate(client, admin_token, project["id"], member["id"])
        assert res.status_code == 502, res.text

        # The previously published summary is preserved.
        detail = await client.get(f"/api/admin/ai/summaries/{summary_id}")
        body = detail.json()
        assert body["published_content"] == "Reviewed publish."
        assert body["last_error_code"] == "GROQ_UNAVAILABLE"
    finally:
        await member_client.aclose()


# ---------------------------------------------------------------------------
# Source overview
# ---------------------------------------------------------------------------
async def test_source_overview_lists_approved_targets(
    client, make_admin, fetch_csrf, monkeypatch
):
    admin_token = await login_admin(client, make_admin, fetch_csrf, email="owner-src@example.com")
    member_client, mtoken, project, member, readable = await _confirmed_member(
        client, admin_token, monkeypatch, email="src@example.com"
    )
    try:
        report = await _submit(member_client, mtoken, project["id"], "Work.")
        await _approve(client, admin_token, report["id"])

        res = await client.get("/api/admin/ai/sources")
        assert res.status_code == 200, res.text
        projects = res.json()["projects"]
        match = next(p for p in projects if p["activity_id"] == project["id"])
        assert match["approved_count"] == 1
        option = match["members"][0]
        assert option["member_id"] == member["id"]
        assert option["member_readable_id"] == readable
        assert option["approved_count"] == 1
        assert option["summary_id"] is None
    finally:
        await member_client.aclose()
