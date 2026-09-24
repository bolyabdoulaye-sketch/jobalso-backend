import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Envoie un email transactionnel. Ne leve jamais d'exception : renvoie True/False."""
    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body_text)
    if body_html:
        msg.add_alternative(body_html, subtype="html")

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email envoye a %s (%s)", to, subject)
        return True
    except Exception:
        logger.exception("Echec d'envoi de l'email a %s (%s)", to, subject)
        return False


def send_welcome_email(to: str, nom_prenom: str) -> bool:
    return send_email(
        to=to,
        subject="Bienvenue sur Jobalso",
        body_text=(
            f"Bonjour {nom_prenom},\n\n"
            "Votre compte Jobalso a bien ete cree.\n\n"
            "L'equipe Jobalso"
        ),
        body_html=(
            f"<p>Bonjour {nom_prenom},</p>"
            "<p>Votre compte Jobalso a bien été créé.</p>"
            "<p>L'équipe Jobalso</p>"
        ),
    )