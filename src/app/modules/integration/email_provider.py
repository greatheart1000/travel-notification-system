from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol

logger = logging.getLogger(__name__)


class EmailProvider(Protocol):
    def send(self, to: str, subject: str, body: str) -> bool:
        """Send a plain-text email. Return True when accepted by the relay."""


@dataclass(slots=True)
class SMTPEmailProvider:
    host: str
    port: int = 465
    username: str = ""
    password: str = ""
    from_name: str = "行程管家"
    use_ssl: bool = True
    timeout: float = 10.0

    def send(self, to: str, subject: str, body: str) -> bool:
        if not self.host or not to:
            return False
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((self.from_name, self.username or self.host))
        message["To"] = to
        message.set_content(body)
        try:
            if self.use_ssl:
                client: smtplib.SMTP = smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout
                )
            else:
                client = smtplib.SMTP(self.host, self.port, timeout=self.timeout)
                client.starttls()
            try:
                if self.username:
                    client.login(self.username, self.password)
                client.send_message(message)
            finally:
                client.quit()
            return True
        except Exception as exc:  # noqa: BLE001 - receipts must never break payment
            logger.warning("email delivery failed: %s", type(exc).__name__)
            return False


class MockEmailProvider:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    def send(self, to: str, subject: str, body: str) -> bool:
        self.sent.append({"to": to, "subject": subject, "body": body})
        return True


def get_email_provider() -> EmailProvider | None:
    host = os.getenv("SMTP_HOST", "").strip()
    username = os.getenv("SMTP_USERNAME", "").strip()
    password = os.getenv("SMTP_PASSWORD", "")
    if not host or not username or not password:
        return None
    try:
        port = int(os.getenv("SMTP_PORT", "465"))
    except ValueError:
        port = 465
    return SMTPEmailProvider(
        host=host,
        port=port,
        username=username,
        password=password,
        from_name=os.getenv("SMTP_FROM_NAME", "行程管家").strip() or "行程管家",
        use_ssl=os.getenv("SMTP_USE_SSL", "true").strip().lower()
        not in {"0", "false", "no"},
    )
