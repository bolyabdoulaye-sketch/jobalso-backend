import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.core.unsubscribe import make_unsubscribe_token

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


def send_notification_email(utilisateur, subject: str, body_text: str, body_html: str | None = None) -> bool:
    """Email de notification : respecte le desabonnement et ajoute le lien (CASL, JA-083).

    A utiliser pour tout email non essentiel (statut de candidature, accuse de reception...).
    """
    if not utilisateur.notifications_email:
        logger.info("Notification ignoree (desabonne) : %s", utilisateur.email)
        return False

    token = make_unsubscribe_token(utilisateur.id_utilisateur)
    url = f"{settings.API_PUBLIC_URL}/api/v1/auth/desabonnement?token={token}"

    text = f"{body_text}\n\n--\nPour ne plus recevoir ces notifications : {url}"
    html = None
    if body_html:
        html = (
            f"{body_html}"
            '<hr style="border:none;border-top:1px solid #DCE7F0;margin:24px 0 12px">'
            '<p style="font-size:12px;color:#587B95">'
            f'<a href="{url}">Se désabonner des notifications par email</a></p>'
        )

    return send_email(
        to=utilisateur.email,
        subject=subject,
        body_text=text,
        body_html=html,
        headers={
            "List-Unsubscribe": f"<{url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    )


def send_welcome_email(to: str, nom_prenom: str) -> bool:
    """Email transactionnel : envoye meme si l'utilisateur est desabonne des notifications."""
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
