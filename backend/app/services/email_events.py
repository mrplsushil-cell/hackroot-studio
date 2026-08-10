"""Templated transactional emails for Hackroot Studio.

Each helper builds a subject + HTML/text body and dispatches through the
configured email provider (mock or smtp). When no SMTP credentials are set the
provider runs in ``mock`` mode (logs instead of sending) and the deployment's
config status reflects that — it never raises into the caller, so a missing
email backend can never break registration, billing, or rendering.
"""
from __future__ import annotations

from app.providers.email import get_email_provider
from app.config import settings

APP_NAME = settings.app_name
FRONTEND_URL = settings.frontend_base_url or "https://app.hackroot.studio"


def provider_status() -> dict:
    """Surface whether real email delivery is configured (no secrets leaked)."""
    return {
        "provider": settings.email_provider,
        "configured": settings.email_provider == "smtp" and bool(settings.smtp_host),
        "from": settings.smtp_from,
    }


def _send(to: str, subject: str, html: str, text: str) -> None:
    try:
        provider = get_email_provider()
        import asyncio
        if asyncio.get_event_loop().is_running():
            asyncio.get_event_loop().create_task(provider.send(to, subject, html, text))
        else:
            asyncio.run(provider.send(to, subject, html, text))
    except Exception as e:  # noqa: BLE001
        # Email must never break the primary operation.
        import logging
        logging.getLogger("app.email").warning("Email send failed for %s: %s", to, e)


def _wrap(title: str, body_html: str) -> tuple[str, str]:
    html = (
        f"<div style='font-family:system-ui,Arial,sans-serif;max-width:520px;margin:auto'>"
        f"<h2 style='color:#7c3aed'>{APP_NAME}</h2>"
        f"<h3>{title}</h3>{body_html}"
        f"<hr/><p style='color:#888;font-size:12px'>© {APP_NAME}</p></div>"
    )
    return html, html.replace("<br/>", "\n").replace("</p>", "\n").replace("<p>", "")


def send_welcome(user) -> None:
    html, text = _wrap(
        "Welcome to Hackroot Studio!",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>Your account is ready. Start generating brand-ready videos in minutes.</p>"
        f"<p><a href='{FRONTEND_URL}/create'>Create your first video →</a></p>",
    )
    _send(user.email, f"Welcome to {APP_NAME}", html, text)


def send_verification(user, token: str) -> None:
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    html, text = _wrap(
        "Verify your email",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>Confirm your address to secure your account:</p>"
        f"<p><a href='{link}'>Verify email</a></p>"
        f"<p>Or use code: <b>{token[:8]}</b></p>",
    )
    _send(user.email, f"Verify your email — {APP_NAME}", html, text)


def send_password_reset(user, token: str) -> None:
    link = f"{FRONTEND_URL}/reset-password?token={token}"
    html, text = _wrap(
        "Reset your password",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>We received a password reset request. This link expires in 30 minutes:</p>"
        f"<p><a href='{link}'>Reset password</a></p>"
        f"<p>If you didn't request this, ignore this email.</p>",
    )
    _send(user.email, f"Password reset — {APP_NAME}", html, text)


def send_payment_success(user, amount_paise: int, plan: str) -> None:
    inr = f"₹{amount_paise/100:,.0f}"
    html, text = _wrap(
        "Payment received",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>We received your payment of <b>{inr}</b> for the <b>{plan}</b> plan.</p>"
        f"<p>Your credits have been added. Happy creating!</p>",
    )
    _send(user.email, f"Payment successful — {APP_NAME}", html, text)


def send_subscription_activated(user, plan: str) -> None:
    html, text = _wrap(
        "Subscription activated",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>Your <b>{plan}</b> subscription is now active. Enjoy priority rendering and more credits.</p>",
    )
    _send(user.email, f"Subscription activated — {APP_NAME}", html, text)


def send_subscription_expiring(user, plan: str, days_left: int) -> None:
    html, text = _wrap(
        "Your subscription is ending soon",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>Your <b>{plan}</b> plan ends in <b>{days_left} days</b>. Renew to avoid losing credits and features.</p>"
        f"<p><a href='{FRONTEND_URL}/billing'>Manage subscription →</a></p>",
    )
    _send(user.email, f"Subscription expiring — {APP_NAME}", html, text)


def send_invoice_generated(user, invoice_no: str, amount_paise: int) -> None:
    inr = f"₹{amount_paise/100:,.0f}"
    html, text = _wrap(
        "Your invoice is ready",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>Invoice <b>{invoice_no}</b> for <b>{inr}</b> has been generated.</p>"
        f"<p><a href='{FRONTEND_URL}/invoices'>View invoices →</a></p>",
    )
    _send(user.email, f"Invoice {invoice_no} — {APP_NAME}", html, text)


def send_video_ready(user, video_title: str, video_id: int) -> None:
    html, text = _wrap(
        "Your video is ready",
        f"<p>Hi {user.full_name or user.email},</p>"
        f"<p>\"{video_title}\" finished rendering and is in your library.</p>"
        f"<p><a href='{FRONTEND_URL}/library?video={video_id}'>View video →</a></p>",
    )
    _send(user.email, f"Video ready — {APP_NAME}", html, text)
