from app.core.config import settings
from app.tests.integration.aides import compte, connecter, entetes, inscrire


def test_inscription_recruteur_cree_son_organisation(client):
    infos, headers = compte(client, "RECRUTEUR", nom_organisation="Cabinet Tremblay", persona="rh")

    moi = client.get("/api/v1/auth/me", headers=headers).json()
    assert moi["id_organisation"] is not None
    assert moi["role_organisation"] == "ADMIN"
    assert moi["persona"] == "rh"
    assert moi["status"] == "EN_ATTENTE"

    organisation = client.get("/api/v1/organisation", headers=headers).json()
    assert organisation["nom"] == "Cabinet Tremblay"


def test_candidat_ne_peut_pas_definir_une_organisation(client):
    reponse = client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidat@exemple.ca",
            "numero_telephone": "+15140000001",
            "mot_de_passe": "MotDePasse123",
            "nom_prenom": "Awa Diop",
            "type_utilisateur": "CANDIDAT",
            "consentement_accepte": True,
            "nom_organisation": "Pirate",
        },
    )
    assert reponse.status_code == 400


def test_inscription_refuse_sans_consentement_et_email_en_double(client):
    infos = inscrire(client, "CANDIDAT")
    doublon = client.post(
        "/api/v1/auth/register",
        json={**{k: infos[k] for k in ("mot_de_passe", "nom_prenom", "type_utilisateur")},
              "email": infos["email"].upper(), "numero_telephone": "+15149999999", "consentement_accepte": True},
    )
    assert doublon.status_code == 400

    sans_consentement = client.post(
        "/api/v1/auth/register",
        json={"email": "x@exemple.ca", "numero_telephone": "+15149999998", "mot_de_passe": "MotDePasse123",
              "nom_prenom": "Sans Accord", "type_utilisateur": "CANDIDAT", "consentement_accepte": False},
    )
    assert sans_consentement.status_code == 400


def test_verification_email(client, boite_mail):
    infos = inscrire(client, "CANDIDAT")
    jeton = boite_mail.jeton(infos["email"], "verifier-email")

    assert client.post("/api/v1/auth/verify-email", json={"token": jeton}).status_code == 200
    headers = entetes(connecter(client, infos["email"]))
    assert client.get("/api/v1/auth/me", headers=headers).json()["status"] == "ACTIF"

    # Le lien ne sert qu'une fois.
    assert client.post("/api/v1/auth/verify-email", json={"token": jeton}).status_code == 400


def test_connexion_insensible_a_la_casse_et_scope(client):
    infos = inscrire(client, "CANDIDAT")
    connecter(client, infos["email"].upper())

    mauvais_espace = client.post(
        "/api/v1/auth/login",
        data={"username": infos["email"], "password": "MotDePasse123", "scope": "recruteur"},
    )
    assert mauvais_espace.status_code == 403

    mauvais_mdp = client.post("/api/v1/auth/login", data={"username": infos["email"], "password": "faux-mdp-123"})
    assert mauvais_mdp.status_code == 401


def test_rafraichissement_avec_rotation_et_detection_de_reutilisation(client):
    infos = inscrire(client, "CANDIDAT")
    jetons = connecter(client, infos["email"])
    assert jetons["expires_in"] == settings.ACCESS_TOKEN_MINUTES * 60

    nouveaux = client.post("/api/v1/auth/refresh", json={"refresh_token": jetons["refresh_token"]})
    assert nouveaux.status_code == 200
    nouveaux = nouveaux.json()
    assert nouveaux["refresh_token"] != jetons["refresh_token"]
    assert client.get("/api/v1/auth/me", headers=entetes(nouveaux)).status_code == 200

    # Réutiliser l'ancien jeton = vol probable : toutes les sessions tombent.
    rejoue = client.post("/api/v1/auth/refresh", json={"refresh_token": jetons["refresh_token"]})
    assert rejoue.status_code == 401
    apres = client.post("/api/v1/auth/refresh", json={"refresh_token": nouveaux["refresh_token"]})
    assert apres.status_code == 401


def test_deconnexion_revoque_la_session(client):
    infos = inscrire(client, "RECRUTEUR")
    jetons = connecter(client, infos["email"])

    assert client.post("/api/v1/auth/logout", json={"refresh_token": jetons["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": jetons["refresh_token"]}).status_code == 401
    # Idempotent
    assert client.post("/api/v1/auth/logout", json={"refresh_token": jetons["refresh_token"]}).status_code == 204


def test_jeton_invalide_refuse(client):
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nimporte.quoi.ici"}).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_mot_de_passe_oublie_puis_reinitialise(client, boite_mail):
    infos = inscrire(client, "CANDIDAT")
    ancienne_session = connecter(client, infos["email"])

    inconnu = client.post("/api/v1/auth/forgot-password", json={"email": "personne@exemple.ca"})
    assert inconnu.status_code == 200
    assert boite_mail.pour("personne@exemple.ca") == []

    assert client.post("/api/v1/auth/forgot-password", json={"email": infos["email"]}).status_code == 200
    jeton = boite_mail.jeton(infos["email"], "reinitialiser-mot-de-passe")

    reponse = client.post(
        "/api/v1/auth/reset-password", json={"token": jeton, "nouveau_mot_de_passe": "NouveauMdp456"}
    )
    assert reponse.status_code == 200

    connecter(client, infos["email"], "NouveauMdp456")
    refuse = client.post("/api/v1/auth/login", data={"username": infos["email"], "password": "MotDePasse123"})
    assert refuse.status_code == 401

    # Le lien meurt avec l'ancien mot de passe, et les anciennes sessions aussi.
    rejoue = client.post("/api/v1/auth/reset-password", json={"token": jeton, "nouveau_mot_de_passe": "Autre789xx"})
    assert rejoue.status_code == 400
    assert client.post(
        "/api/v1/auth/refresh", json={"refresh_token": ancienne_session["refresh_token"]}
    ).status_code == 401


def test_jeton_de_reinitialisation_falsifie(client):
    infos = inscrire(client, "CANDIDAT")
    faux = f"{infos['id_utilisateur']}.9999999999.{'0' * 64}"
    reponse = client.post("/api/v1/auth/reset-password", json={"token": faux, "nouveau_mot_de_passe": "Pirate12345"})
    assert reponse.status_code == 400


def test_changement_de_mot_de_passe(client):
    infos = inscrire(client, "CANDIDAT")
    headers = entetes(connecter(client, infos["email"]))

    faux = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": "pas-le-bon", "nouveau_mot_de_passe": "NouveauMdp456"},
        headers=headers,
    )
    assert faux.status_code == 400

    ok = client.post(
        "/api/v1/auth/change-password",
        json={"ancien_mot_de_passe": "MotDePasse123", "nouveau_mot_de_passe": "NouveauMdp456"},
        headers=headers,
    )
    assert ok.status_code == 200
    connecter(client, infos["email"], "NouveauMdp456")


def test_mot_de_passe_trop_long_refuse(client):
    reponse = client.post(
        "/api/v1/auth/register",
        json={"email": "long@exemple.ca", "numero_telephone": "+15140000077", "mot_de_passe": "é" * 40,
              "nom_prenom": "Trop Long", "type_utilisateur": "CANDIDAT", "consentement_accepte": True},
    )
    assert reponse.status_code == 422


def test_limite_de_tentatives_de_connexion(client):
    infos = inscrire(client, "CANDIDAT")
    settings.RATE_LIMIT_ENABLED = True
    # Les connexions réussies ne consomment pas le quota d'échecs.
    for _ in range(3):
        connecter(client, infos["email"])

    codes = [
        client.post("/api/v1/auth/login", data={"username": infos["email"], "password": "mauvais-mdp"}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_sante(client):
    reponse = client.get("/health")
    assert reponse.status_code == 200
    assert reponse.json()["database"] == "ok"
