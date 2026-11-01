"""Watch alert email (ADR-0020): a digest of source changes that touch tracked applications.

Plain SMTP to a relay the operator configures. The digest says which cited source changed and
which tracked applications cite it; like the Watch it draws no conclusion beyond "re-verify"."""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from collections.abc import Callable
from email.message import EmailMessage

from pydantic import BaseModel

from app.config import Settings
from app.planner.digest import WatchItem


class AlertConfig(BaseModel):
    host: str
    port: int
    user: str = ""
    password: str = ""
    security: str = "starttls"
    sender: str
    recipients: list[str]
    web_url: str = ""

    @classmethod
    def from_settings(cls, s: Settings) -> AlertConfig | None:
        """None when alerts are not fully configured (no host, sender or recipients)."""
        recipients = [r.strip() for r in s.alert_recipients.split(",") if r.strip()]
        if not (s.smtp_host and s.alert_from and recipients):
            return None
        return cls(host=s.smtp_host, port=s.smtp_port, user=s.smtp_user, password=s.smtp_password,
                   security=s.smtp_security, sender=s.alert_from, recipients=recipients,
                   web_url=s.public_web_url.rstrip("/"))


def _line(item: WatchItem) -> str:
    c = item.change
    where = ", ".join(item.jurisdictions)
    if c.kind == "changed":
        what = f"text changed (+{c.words_added}/-{c.words_removed} words)"
    elif c.kind == "published":
        what = f"new publication matching the feed's keywords: {c.detail}"
    else:
        what = f"source unreachable ({c.detail})"
    if c.ai_summary:
        what += f"\n  AI-assisted triage ({c.materiality}, unverified): {c.ai_summary}"
    apps = ", ".join(f"{a.license_id} [{a.status}]" for a in item.affected)
    return f"- {where}: {what}\n  {c.url}\n  Tracked applications: {apps}"


def render_digest(items: list[WatchItem], web_url: str = "") -> tuple[str, str]:
    """(subject, plain-text body). Items must be non-empty."""
    n = len(items)
    subject = f"ComplianceOS Watch: {n} source change{'s' if n != 1 else ''} touching your applications"
    body = ["The Watch found changes in sources cited by licences you are tracking.", "",
            *(_line(i) for i in items), "",
            items[0].advice,
            "The Watch compares text; it does not say what a change means."]
    if web_url:
        body += ["", f"Open the planner: {web_url}/?from=alert"]
    return subject, "\n".join(body) + "\n"


def build_message(cfg: AlertConfig, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = cfg.sender
    msg["To"] = ", ".join(cfg.recipients)
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


Sender = Callable[[AlertConfig, EmailMessage], None]


def smtp_send(cfg: AlertConfig, msg: EmailMessage) -> None:
    """Blocking SMTP delivery. TLS certificates are verified for starttls and ssl."""
    ctx = ssl.create_default_context()
    if cfg.security == "ssl":
        client: smtplib.SMTP = smtplib.SMTP_SSL(cfg.host, cfg.port, timeout=30, context=ctx)
    else:
        client = smtplib.SMTP(cfg.host, cfg.port, timeout=30)
    with client:
        if cfg.security == "starttls":
            client.starttls(context=ctx)
        if cfg.user:
            client.login(cfg.user, cfg.password)
        client.send_message(msg)


async def send_digest(cfg: AlertConfig, items: list[WatchItem],
                      sender: Sender = smtp_send) -> bool:
    """Send one digest; False (and nothing sent) when there is nothing to report."""
    if not items:
        return False
    subject, body = render_digest(items, cfg.web_url)
    await asyncio.to_thread(sender, cfg, build_message(cfg, subject, body))
    return True
