"""Minimal email service for the member feature.

Deliberately NOT a generic messaging platform: it exists to deliver a single
kind of mail — account onboarding links. Two transports are provided:

- **smtp**  — real delivery via the configured `SMTP_*` environment variables
  (STARTTLS when the server supports it, optional login).
- **log**   — mock/dev transport that never touches the network and only logs
  the rendered message. Used when `SMTP_HOST` is unset or `EMAIL_MOCK=true`,
  so development and tests can never accidentally send real mail.

The onboarding link is the only sensitive content; it is never logged by the
smtp transport (only recipient + subject), and only logged verbatim by the
log transport, which is used solely in non-delivery mode.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger("email")


class EmailDeliveryError(RuntimeError):
    """Raised when an email could not be queued to the delivery transport."""


@dataclass(frozen=True)
class EmailAttachment:
    """A single file attached to an outgoing message."""

    filename: str
    content: bytes
    mime_type: str = "application/pdf"


@dataclass(frozen=True)
class EmailMessageSpec:
    to: str
    subject: str
    text: str
    attachments: tuple[EmailAttachment, ...] = ()


def _split_mime(mime_type: str) -> tuple[str, str]:
    if "/" in mime_type:
        maintype, subtype = mime_type.split("/", 1)
        return maintype or "application", subtype or "octet-stream"
    return "application", "octet-stream"


class EmailTransport:
    """Interface implemented by both transports."""

    mode: str = "base"

    async def send(self, message: EmailMessageSpec) -> None:
        raise NotImplementedError


@dataclass
class LoggingEmailTransport(EmailTransport):
    """Never sends anything: logs the full rendered message. The only safe
    transport in development/tests — real addresses are never touched."""

    mode: str = "log"
    prefix: str = "EMAIL"

    async def send(self, message: EmailMessageSpec) -> None:
        log.info(
            "%s to=%s subject=%s attachments=%d\n%s",
            self.prefix,
            message.to,
            message.subject,
            len(message.attachments),
            message.text,
        )


@dataclass
class SmtpEmailTransport(EmailTransport):
    """Real SMTP delivery via smtplib (runs in a worker thread so the event
    loop is never blocked). Content is never logged."""

    mode: str = "smtp"
    host: str = ""
    port: int = 587
    username: str | None = None
    password: str | None = None
    from_email: str = ""
    _smtp_kwargs: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._smtp_kwargs = {"timeout": 15}

    def _send_sync(self, message: EmailMessageSpec) -> None:
        if not self.host:
            raise EmailDeliveryError("SMTP_HOST is not configured")
        if not self.from_email:
            raise EmailDeliveryError("SMTP_FROM_EMAIL is not configured")

        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.text)
        for attachment in message.attachments:
            maintype, subtype = _split_mime(attachment.mime_type)
            msg.add_attachment(
                attachment.content,
                maintype=maintype,
                subtype=subtype,
                filename=attachment.filename,
            )

        envelope_from = self.from_email
        try:
            if self.port == 465:
                context = ssl.create_default_context()
                client = smtplib.SMTP_SSL(
                    self.host, self.port, context=context, timeout=15
                )
            else:
                client = smtplib.SMTP(self.host, self.port, timeout=15)
                try:
                    client.starttls()
                except smtplib.SMTPNotSupportedError:
                    # Plaintext is refused when credentials are used.
                    if self.username:
                        raise EmailDeliveryError(
                            "SMTP server does not support STARTTLS; refusing to "
                            "send plaintext credentials"
                        )
            try:
                if self.username:
                    client.login(self.username, self.password or "")
                client.send_message(msg, from_addr=envelope_from, to_addrs=[message.to])
            finally:
                try:
                    client.quit()
                except smtplib.SMTPServerDisconnected:
                    pass
        except EmailDeliveryError:
            raise
        except (smtplib.SMTPException, OSError) as exc:
            raise EmailDeliveryError(f"SMTP delivery failed: {type(exc).__name__}") from exc


_get_transport_cache: dict | None = None


def get_email_transport() -> EmailTransport:
    """Build the configured transport. Cached per process; tests clear the
    cache or monkeypatch `get_email_transport` to capture deliveries."""
    global _get_transport_cache
    settings = get_settings()
    if _get_transport_cache is None:
        if settings.EMAIL_MOCK or not settings.SMTP_HOST:
            _get_transport_cache = LoggingEmailTransport()
        else:
            _get_transport_cache = SmtpEmailTransport(
                host=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=(
                    settings.SMTP_USERNAME.get_secret_value()
                    if settings.SMTP_USERNAME
                    else None
                ),
                password=(
                    settings.SMTP_PASSWORD.get_secret_value()
                    if settings.SMTP_PASSWORD
                    else None
                ),
                from_email=settings.SMTP_FROM_EMAIL or "",
            )
    return _get_transport_cache


def reset_email_transport() -> None:
    """Drop the cached transport (used by tests after changing settings)."""
    global _get_transport_cache
    _get_transport_cache = None


async def send_email(
    *,
    to: str,
    subject: str,
    text: str,
    attachments: tuple[EmailAttachment, ...] = (),
) -> None:
    """Deliver one email through the configured transport.

    Raises `EmailDeliveryError` when delivery cannot be completed — callers
    (the members service) surface that clearly and let admins retry via the
    resend endpoint.
    """
    message = EmailMessageSpec(to=to, subject=subject, text=text, attachments=attachments)
    transport = get_email_transport()
    try:
        if transport.mode == "smtp":
            # smtplib is blocking; keep it off the event loop.
            await asyncio.to_thread(transport._send_sync, message)  # noqa: SLF001
        else:
            await transport.send(message)
    except EmailDeliveryError:
        raise
    except Exception as exc:  # defensive: never turn a crash into a member bug
        log.exception("Email delivery failed unexpectedly")
        raise EmailDeliveryError(f"Email delivery failed: {type(exc).__name__}") from exc