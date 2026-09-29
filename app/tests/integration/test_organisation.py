from app.tests.integration.aides import compte, connecter, creer_offre, entetes, inscrire


def _inviter_et_rejoindre(client, boite_mail, headers_admin):
    """Invite un nouveau recruteur, qui accepte : retourne ses en-têtes."""
    invite = inscrire(client, "RECRUTEUR")
    reponse = client.post(
        "/api/v1/organisation/invitations", json={"email": invite["email"]}, headers=headers_admin
    )
    assert reponse.status_code == 201, reponse.text
    headers = entetes(connecter(client, invite["email"]))
    jeton = boite_mail.jeton(invite["email"], "invitation")
    accepte = client.post("/api/v1/organisation/invitations/accept", json={"token": jeton}, headers=headers)
    assert accepte.status_code == 200, accepte.text
    return invite, headers


def test_nouveau_recruteur_peut_publier_une_offre(client):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)

    assert offre["status"] is True
    assert len(offre["criteres"]) == 3
    assert [o["id_offre"] for o in client.get("/api/v1/offres/", headers=headers).json()] == [offre["id_offre"]]


def test_invitation_par_email_sans_jeton_dans_l_api(client, boite_mail):
    _, headers = compte(client, "RECRUTEUR")
    reponse = client.post("/api/v1/organisation/invitations", json={"email": "Nouveau@Exemple.ca"}, headers=headers)

    assert reponse.status_code == 201
    assert "token" not in reponse.json()
    assert "token" not in client.get("/api/v1/organisation/invitations", headers=headers).json()[0]
    assert boite_mail.jeton("nouveau@exemple.ca", "invitation")

    doublon = client.post("/api/v1/organisation/invitations", json={"email": "nouveau@exemple.ca"}, headers=headers)
    assert doublon.status_code == 409


def test_un_candidat_ne_peut_pas_rejoindre_une_organisation(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    candidat, headers_candidat = compte(client, "CANDIDAT")

    refuse = client.post(
        "/api/v1/organisation/invitations", json={"email": candidat["email"]}, headers=headers_admin
    )
    assert refuse.status_code == 400

    # Même avec une invitation émise avant la création du compte candidat.
    client.post("/api/v1/organisation/invitations", json={"email": "futur@exemple.ca"}, headers=headers_admin)
    jeton = boite_mail.jeton("futur@exemple.ca", "invitation")
    _, headers_futur = compte(client, "CANDIDAT", email="futur@exemple.ca")
    accepte = client.post("/api/v1/organisation/invitations/accept", json={"token": jeton}, headers=headers_futur)
    assert accepte.status_code == 403

    assert client.get("/api/v1/offres/", headers=headers_candidat).status_code == 403


def test_invitation_pour_un_autre_email_refusee(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    client.post("/api/v1/organisation/invitations", json={"email": "cible@exemple.ca"}, headers=headers_admin)
    jeton = boite_mail.jeton("cible@exemple.ca", "invitation")

    _, headers_autre = compte(client, "RECRUTEUR")
    reponse = client.post("/api/v1/organisation/invitations/accept", json={"token": jeton}, headers=headers_autre)
    assert reponse.status_code == 403


def test_collaboration_dans_l_organisation(client, boite_mail, stockage):
    admin, headers_admin = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers_admin)
    _, headers_membre = _inviter_et_rejoindre(client, boite_mail, headers_admin)

    membres = client.get("/api/v1/organisation/membres", headers=headers_membre).json()
    assert sorted(m["role"] for m in membres) == ["ADMIN", "MEMBRE"]

    # Le membre voit et modifie l'offre de sa collègue.
    assert client.get(f"/api/v1/offres/{offre['id_offre']}", headers=headers_membre).status_code == 200
    modif = client.put(
        f"/api/v1/offres/{offre['id_offre']}", json={"titre_offre": "Developpeur senior"}, headers=headers_membre
    )
    assert modif.status_code == 200
    assert modif.json()["titre_offre"] == "Developpeur senior"

    # Il suit la shortlist et fait avancer le pipeline.
    from app.tests.integration.aides import DOCX_MIME, docx

    client.post(
        f"/api/v1/public/offres/{offre['lien_token']}/postuler",
        data={"nom_prenom": "Awa Diop", "email": "awa@exemple.ca", "numero_telephone": "+15145550001",
              "consentement_accepte": "true"},
        files={"fichier_cv": ("cv.docx", docx(), DOCX_MIME)},
    )
    resultats = client.get(f"/api/v1/offres/{offre['id_offre']}/resultats", headers=headers_membre).json()
    assert len(resultats) == 1
    statut = client.patch(
        f"/api/v1/offres/resultats/{resultats[0]['id_resultat']}/statut",
        json={"statut": "EN_REVUE"},
        headers=headers_membre,
    )
    assert statut.status_code == 200

    # Mais seule l'autrice (ou un ADMIN) peut supprimer l'offre.
    assert client.delete(f"/api/v1/offres/{offre['id_offre']}", headers=headers_membre).status_code == 403
    assert client.delete(f"/api/v1/offres/{offre['id_offre']}", headers=headers_admin).status_code == 204


def test_rejoindre_remplace_l_organisation_vide_mais_pas_une_active(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    invite, headers_invite = compte(client, "RECRUTEUR")
    creer_offre(client, headers_invite)  # son organisation n'est plus vide

    client.post("/api/v1/organisation/invitations", json={"email": invite["email"]}, headers=headers_admin)
    jeton = boite_mail.jeton(invite["email"], "invitation")
    refuse = client.post("/api/v1/organisation/invitations/accept", json={"token": jeton}, headers=headers_invite)
    assert refuse.status_code == 409


def test_isolation_entre_organisations(client, boite_mail):
    _, headers_a = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers_a)
    _, headers_b = compte(client, "RECRUTEUR")

    for methode, url, corps in [
        ("get", f"/api/v1/offres/{offre['id_offre']}", None),
        ("put", f"/api/v1/offres/{offre['id_offre']}", {"titre_offre": "Pirate"}),
        ("delete", f"/api/v1/offres/{offre['id_offre']}", None),
        ("get", f"/api/v1/offres/{offre['id_offre']}/resultats", None),
    ]:
        reponse = client.request(methode, url, json=corps, headers=headers_b)
        assert reponse.status_code == 404, (methode, url, reponse.status_code)
    assert client.get("/api/v1/offres/", headers=headers_b).json() == []


def test_membre_retire_puis_nouvelle_organisation(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    invite, headers_membre = _inviter_et_rejoindre(client, boite_mail, headers_admin)

    moi = client.get("/api/v1/auth/me", headers=headers_membre).json()
    assert client.delete(f"/api/v1/organisation/membres/{moi['id_utilisateur']}", headers=headers_admin).status_code == 204
    assert client.get("/api/v1/offres/", headers=headers_membre).status_code == 403

    cree = client.post("/api/v1/organisation", json={"nom": "Mon agence"}, headers=headers_membre)
    assert cree.status_code == 201
    assert client.post("/api/v1/organisation", json={"nom": "Deuxieme"}, headers=headers_membre).status_code == 409
    creer_offre(client, headers_membre)


def test_seul_un_admin_gere_l_equipe(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    _, headers_membre = _inviter_et_rejoindre(client, boite_mail, headers_admin)

    assert client.post(
        "/api/v1/organisation/invitations", json={"email": "x@exemple.ca"}, headers=headers_membre
    ).status_code == 403
    assert client.patch("/api/v1/organisation", json={"nom": "Renomme"}, headers=headers_membre).status_code == 403
    renomme = client.patch("/api/v1/organisation", json={"nom": "Renomme"}, headers=headers_admin)
    assert renomme.json()["nom"] == "Renomme"


def test_quitter_une_organisation(client, boite_mail):
    _, headers_admin = compte(client, "RECRUTEUR")
    # Seul membre : impossible de laisser l'organisation vide.
    assert client.post("/api/v1/organisation/quitter", headers=headers_admin).status_code == 400

    _, headers_membre = _inviter_et_rejoindre(client, boite_mail, headers_admin)
    # Seul ADMIN : il doit d'abord nommer un autre administrateur.
    assert client.post("/api/v1/organisation/quitter", headers=headers_admin).status_code == 400

    assert client.post("/api/v1/organisation/quitter", headers=headers_membre).status_code == 204
    assert client.get("/api/v1/offres/", headers=headers_membre).status_code == 403
    assert len(client.get("/api/v1/organisation/membres", headers=headers_admin).json()) == 1
