"""Email provider abstraction.

Two backends:
  * ``mock``  — logs the email and (optionally) records it; safe for dev/test.
  * ``smtp``  — sends via the configured SMTP server.

A typed helper ``send_notification_email`` maps notification types to subjects.
Secrets (SMTP password) are never exposed via API.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Protocol

from app.config import settings

log = logging.getLogger("hackroot.email")


class EmailProvider(Protocol):
    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> None: ...


class MockEmailProvider:
    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        log.info("[email:mock] -> %s | %s", to, subject)


class SmtpEmailProvider:
    def __init__(self) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_password
        self.sender = settings.smtp_from

    async def send(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.sender
        msg["To"] = to
        msg.set_content(text or html)
        msg.add_alternative(html, subtype="html")
        try:
            with smtplib.SMTP(self.host, self.port) as s:
                s.starttls()
                if self.user:
                    s.login(self.user, self.password)
                s.send_message(msg)
        except Exception as e:  # noqa: BLE001
            log.warning("SMTP send failed to %s: %s", to, e)


def get_email_provider() -> EmailProvider:
    if settings.email_provider == "smtp" and settings.smtp_host:
        return SmtpEmailProvider()
    return MockEmailProvider()


# Notification-type -> subject templates (welcome, verify, reset, etc.)
SUBJECTS = {
    "welcome": "Welcome to Hackroot Studio",
    "verify_email": "Verify your email — Hackroot Studio",
    "password_reset": "Reset your Hackroot Studio password",
    "payment_success": "Payment received — Hackroot Studio",
    "subscription_activated": "Your subscription is active — Hackroot Studio",
    "subscription_expiring": "Your subscription expires soon — Hackroot Studio",
    "payment_failed": "Payment failed — Hackroot Studio",
    "invoice_generated": "Your invoice is ready — Hackroot Studio",
    "video_ready": "Your video is ready — Hackroot Studio",
}


async def send_notification_email(to: str, kind: str, html: str, text: str | None = None) -> None:
    subject = SUBJECTS.get(kind, "Hackroot Studio")
    provider = get_email_provider()
    await provider.send(to, subject, html, text)
