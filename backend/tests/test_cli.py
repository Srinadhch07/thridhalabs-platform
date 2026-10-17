"""`python -m app.cli.create_admin` — interactive admin provisioning."""

from __future__ import annotations

import pytest

from app.cli import create_admin as cli
from app.db.mongo import get_mongo

PASSWORD = "Str0ngPass!2026"


def _queue(*answers: str):
    it = iter(answers)

    def _next(_prompt: str) -> str:
        try:
            return next(it)
        except StopIteration:  # pragma: no cover - test input exhaustion
            raise EOFError from None

    return _next


async def test_cli_creates_admin_without_leaking_password(client, capsys):
    code = await cli.run(
        ["--role", "owner"],
        input_func=_queue("cli-owner@example.com"),
        getpass_func=_queue(PASSWORD, PASSWORD),
    )
    out = capsys.readouterr().out

    assert code == 0
    assert "cli-owner@example.com" in out
    assert "role=owner" in out
    assert PASSWORD not in out, "password must never be printed"


async def test_cli_creates_non_owner_role_via_prompt(client, capsys):
    code = await cli.run(
        [],
        input_func=_queue("cli-editor@example.com", "editor"),
        getpass_func=_queue(PASSWORD, PASSWORD),
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "role=editor" in out


async def test_cli_rejects_duplicate_email(client, capsys):
    first = await cli.run(
        ["--role", "admin"],
        input_func=_queue("dupe-cli@example.com"),
        getpass_func=_queue(PASSWORD, PASSWORD),
    )
    capsys.readouterr()
    assert first == 0

    second = await cli.run(
        ["--role", "admin"],
        input_func=_queue("dupe-cli@example.com"),
        getpass_func=_queue(),
    )
    out = capsys.readouterr().out
    assert second == 1
    assert "already exists" in out


async def test_cli_retries_on_invalid_email_then_weak_password(client, capsys):
    code = await cli.run(
        ["--role", "editor"],
        input_func=_queue("not-an-email", "cli-retry@example.com"),
        getpass_func=_queue("short", "short", PASSWORD, PASSWORD),
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "valid email address" in out
    assert "at least 10 characters" in out
    assert "cli-retry@example.com" in out


async def test_cli_retries_on_password_mismatch(client, capsys):
    code = await cli.run(
        ["--role", "owner"],
        input_func=_queue("mismatch@example.com"),
        getpass_func=_queue(PASSWORD, "Different!Pass99", PASSWORD, PASSWORD),
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Passwords do not match" in out


async def test_cli_retries_on_unknown_role(client, capsys):
    code = await cli.run(
        [],
        input_func=_queue("role@example.com", "boss", "admin"),
        getpass_func=_queue(PASSWORD, PASSWORD),
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Unknown role" in out
    assert "role=admin" in out


async def test_cli_aborts_on_closed_input(client):
    with pytest.raises(SystemExit):
        await cli.run(
            [],
            input_func=lambda _p: (_ for _ in ()).throw(EOFError),
            getpass_func=_queue(PASSWORD, PASSWORD),
        )


async def test_cli_persists_normalized_email(client, capsys):
    code = await cli.run(
        ["--role", "owner"],
        input_func=_queue("  Normalized.CLI@Example.com "),
        getpass_func=_queue(PASSWORD, PASSWORD),
    )
    assert code == 0

    # cli.run() closes the shared client on exit — reconnect for the assertions.
    await get_mongo().connect()
    doc = await get_mongo().database["admins"].find_one(
        {"email": "normalized.cli@example.com"}
    )
    assert doc is not None
    assert doc["password_hash"].startswith("$2")
    assert PASSWORD not in doc["password_hash"]
