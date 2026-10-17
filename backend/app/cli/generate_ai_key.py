"""Generate a dedicated encryption key for the AI settings secret store.

Usage (from `backend/`, with the virtualenv active):

    python -m app.cli.generate_ai_key

The value is printed to standard output **only** — it is never persisted by the
application. The operator copies it into ``AI_SETTINGS_ENCRYPTION_KEY`` in the
environment/secret manager (never into a Git-tracked file). This key is used to
encrypt the dynamic Groq API key at rest and is unrelated to ``JWT_SECRET``.
"""

from __future__ import annotations

import argparse
import secrets
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.generate_ai_key",
        description=(
            "Print a fresh, high-entropy value for AI_SETTINGS_ENCRYPTION_KEY "
            "(printed only, never stored)."
        ),
    )
    parser.add_argument(
        "--bytes",
        type=int,
        default=48,
        help="Entropy in bytes before URL-safe encoding (default: 48)",
    )
    return parser


def run(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.bytes < 32:
        print("Error: --bytes must be at least 32.", file=sys.stderr)
        return 1
    print(secrets.token_urlsafe(args.bytes))
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
