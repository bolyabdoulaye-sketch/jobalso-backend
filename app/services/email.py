import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    headers: dict[str, str] | None = None,
) -> bool:
    """Envoie un email. Ne leve jamais d'exception : renvoie True/False."""
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject

    for name, value in (headers or {}).items():
        msg[name] = value

    msg.set_content(body_text)

    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=10,
        ) as server:
            if settings.SMTP_TLS:
                server.starttls()

            if settings.SMTP_USER:
                server.login(
                    settings.SMTP_USER,
                    settings.SMTP_PASSWORD,
                )

            server.send_message(msg)

        logger.info("Email envoye a %s (%s)", to, subject)
        return True

    except Exception:
        logger.exception(
            "Echec d'envoi de l'email a %s (%s)",
            to,
            subject,
        )
        return False