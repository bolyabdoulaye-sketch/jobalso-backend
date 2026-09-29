from html import escape

from app.services.email import send_email


def send_verification_email(to: str, nom_prenom: str, verification_url: str) -> bool:
    """Confirmation de l'adresse email apres l'inscription."""
    text = (
        f"Bonjour {nom_prenom},\n\n"
        "Bienvenue sur Jobalso. Confirmez votre adresse email avec ce lien "
        f"(valable 7 jours) : {verification_url}\n\n"
        "Si vous n'avez pas cree de compte, ignorez cet email.\n\n"
        "L'equipe Jobalso"
    )
    html = (
        f"<p>Bonjour {escape(nom_prenom)},</p>"
        "<p>Bienvenue sur Jobalso. "
        f'<a href="{escape(verification_url)}">Confirmez votre adresse email</a> '
        "(lien valable 7 jours).</p>"
        "<p>Si vous n'avez pas créé de compte, ignorez cet email.</p>"
        "<p>L'équipe Jobalso</p>"
    )
    return send_email(
        to=to,
        subject="Confirmez votre adresse email Jobalso",
        body_text=text,
        body_html=html,
    )


def send_invitation_email(to: str, nom_organisation: str, invitation_url: str) -> bool:
    """Invitation a rejoindre une organisation (JA-008)."""
    nom_sujet = " ".join(nom_organisation.split())
    text = (
        "Bonjour,\n\n"
        f"Vous etes invite a rejoindre l'organisation « {nom_organisation} » sur Jobalso.\n\n"
        f"Acceptez l'invitation (lien valable 7 jours) : {invitation_url}\n\n"
        "Il vous faudra un compte recruteur avec cette adresse email.\n\n"
        "L'equipe Jobalso"
    )
    html = (
        "<p>Bonjour,</p>"
        f"<p>Vous êtes invité à rejoindre l'organisation « {escape(nom_organisation)} » sur Jobalso.</p>"
        f'<p><a href="{escape(invitation_url)}">Accepter l\'invitation</a> (lien valable 7 jours)</p>'
        "<p>Il vous faudra un compte recruteur avec cette adresse email.</p>"
        "<p>L'équipe Jobalso</p>"
    )
    return send_email(
        to=to,
        subject=f"Invitation à rejoindre {nom_sujet} sur Jobalso",
        body_text=text,
        body_html=html,
    )
