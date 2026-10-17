"""Provision an admin account interactively.

Usage (from `backend/`, with the virtualenv active):

    python -m app.cli.create_admin
    python -m app.cli.create_admin --role editor

The password is only ever read from a hidden prompt — never from command
line arguments (argv would be visible in shell history and process lists).
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
from typing import Callable

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.errors import AppError
from app.core.security import validate_password_policy
from app.db.mongo import get_mongo
from app.models.admin import Role, normalize_email
from app.modules.admins import repository
from app.modules.admins.service import create_admin

InputFunc = Callable[[str], str]
GetpassFunc = Callable[[str], str]

_email_syntax = TypeAdapter(EmailStr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.create_admin",
        description="Create a Thridha Labs admin account (password is prompted, never argv).",
    )
    parser.add_argument(
        "--role",
        choices=[role.value for role in Role],
        default=None,
        help="Role for the new account (default: prompt, default owner)",
    )
    return parser


def _read_line(prompt: str, input_func: InputFunc) -> str:
    try:
        return input_func(prompt)
    except EOFError:
        raise SystemExit("\nInput closed — aborting.") from None


def _prompt_email(input_func: InputFunc) -> str:
    while True:
        raw = _read_line("Email: ", input_func)
        email = normalize_email(raw)
        if not email:
            print("Email must not be empty.")
            continue
        try:
            _email_syntax.validate_python(email)
        except ValidationError:
            print("Please enter a valid email address.")
            continue
        return email


def _prompt_password(getpass_func: GetpassFunc, input_func: InputFunc) -> str:
    while True:
        try:
            password = getpass_func("Password: ")
            confirm = getpass_func("Confirm password: ")
        except EOFError:
            raise SystemExit("\nInput closed — aborting.") from None
        if password != confirm:
            print("Passwords do not match — try again.")
            continue
        try:
            validate_password_policy(password)
        except AppError as exc:
            print(f"{exc.message} — try again.")
            continue
        return password


def _prompt_role(input_func: InputFunc) -> Role:
    choices = "/".join(role.value for role in Role)
    while True:
        raw = _read_line(f"Role [{choices}] (default: owner): ", input_func).strip().lower()
        if not raw:
            return Role.OWNER
        try:
            return Role(raw)
        except ValueError:
            print(f"Unknown role '{raw}' — choose one of: {choices}")


async def run(
    argv: list[str] | None = None,
    *,
    input_func: InputFunc = input,
    getpass_func: GetpassFunc = getpass.getpass,
) -> int:
    args = build_parser().parse_args(argv)

    if not await get_mongo().connect():
        print("Error: cannot reach MongoDB — aborting.")
        await get_mongo().close()
        return 1

    try:
        email = _prompt_email(input_func)

        if await repository.email_exists(email):
            print(f"Error: an admin with the email '{email}' already exists.")
            return 1

        password = _prompt_password(getpass_func, input_func)

        if args.role:
            role = Role(args.role)
        else:
            role = _prompt_role(input_func)

        admin = await create_admin(email, password, role)
        # Success message contains no secrets.
        print(f"Created admin account: {admin.email} (role={admin.role.value}, id={admin.id})")
        return 0
    except AppError as exc:
        print(f"Error: {exc.message}")
        return 1
    finally:
        await get_mongo().close()


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
