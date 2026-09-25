from html import escape

from app.services.email import send_email


def send_password_reset_email(to: str, nom_prenom: str, reset_url: str) -> bool:
    """Email transactionnel : lien de reinitialisation, valable 30 minutes (JA-004)."""
    text = (
        f"Bonjour {nom_prenom},\n\n"
        "Vous avez demande a reinitialiser votre mot de passe Jobalso.\n\n"
        f"Cliquez sur ce lien (valable 30 minutes) : {reset_url}\n\n"
        "Si vous n'etes pas a l'origine de cette demande, ignorez cet email : "
        "votre mot de passe actuel reste inchange.\n\n"
        "L'equipe Jobalso"
    )
    html = (
        f"<p>Bonjour {escape(nom_prenom)},</p>"
        "<p>Vous avez demandé à réinitialiser votre mot de passe Jobalso.</p>"
        f'<p><a href="{reset_url}">Réinitialiser mon mot de passe</a> (valable 30 minutes)</p>'
        "<p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : "
        "votre mot de passe actuel reste inchangé.</p>"
        "<p>L'équipe Jobalso</p>"
    )
    return send_email(
        to=to,
        subject="Réinitialisation de votre mot de passe Jobalso",
        body_text=text,
        body_html=html,
    )
