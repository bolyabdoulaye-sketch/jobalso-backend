from html import escape

from app.services.email import send_email


def send_application_receipt_email(
    to: str,
    nom_prenom: str,
    titre_offre: str,
    code_cv: str,
    activation_url: str | None = None,
) -> bool:
    """Accuse de reception d'une candidature (JA-081). Email transactionnel.

    Pour un compte cree par la candidature publique, `activation_url` permet
    au candidat de choisir son mot de passe et d'acceder a son espace.
    """
    titre_sujet = " ".join(titre_offre.split())  # pas de retour a la ligne dans l'en-tete

    texte_activation = ""
    html_activation = ""
    if activation_url:
        texte_activation = (
            "Un espace candidat a ete cree pour vous. Choisissez votre mot de passe "
            f"pour suivre votre candidature (lien valable 7 jours) : {activation_url}\n\n"
        )
        html_activation = (
            "<p>Un espace candidat a été créé pour vous. "
            f'<a href="{escape(activation_url)}">Choisissez votre mot de passe</a> '
            "pour suivre votre candidature (lien valable 7 jours).</p>"
        )

    text = (
        f"Bonjour {nom_prenom},\n\n"
        f"Nous avons bien reçu votre candidature pour le poste « {titre_offre} ».\n\n"
        f"Votre code CV : {code_cv}\n\n"
        f"{texte_activation}"
        "Vous serez informé par email de l'évolution de votre candidature.\n\n"
        "L'équipe Jobalso"
    )
    html = (
        f"<p>Bonjour {escape(nom_prenom)},</p>"
        f"<p>Nous avons bien reçu votre candidature pour le poste « {escape(titre_offre)} ».</p>"
        f"<p>Votre code CV : <strong>{escape(code_cv)}</strong></p>"
        f"{html_activation}"
        "<p>Vous serez informé par email de l'évolution de votre candidature.</p>"
        "<p>L'équipe Jobalso</p>"
    )
    return send_email(
        to=to,
        subject=f"Candidature reçue : {titre_sujet}",
        body_text=text,
        body_html=html,
    )
