import io
import zipfile

from app.tests.integration.aides import DOCX_MIME, compte, connecter, creer_offre, docx, entetes, pdf


def _postuler_public(client, lien_token, email="awa@exemple.ca", telephone="+15145550001", fichier=None,
                     nom="Awa Diop", **extra):
    fichier = fichier or ("cv.docx", docx(), DOCX_MIME)
    return client.post(
        f"/api/v1/public/offres/{lien_token}/postuler",
        data={"nom_prenom": nom, "email": email, "numero_telephone": telephone,
              "consentement_accepte": "true", **extra},
        files={"fichier_cv": fichier},
    )


def test_candidature_publique_puis_activation_du_compte(client, boite_mail, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)

    reponse = _postuler_public(client, offre["lien_token"])
    assert reponse.status_code == 201, reponse.text
    assert len(stockage.fichiers) == 1

    # L'accusé de réception contient le lien pour choisir son mot de passe.
    jeton = boite_mail.jeton("awa@exemple.ca", "reinitialiser-mot-de-passe")
    active = client.post("/api/v1/auth/reset-password", json={"token": jeton, "nouveau_mot_de_passe": "MonMotDePasse1"})
    assert active.status_code == 200

    headers_candidat = entetes(connecter(client, "awa@exemple.ca", "MonMotDePasse1"))
    moi = client.get("/api/v1/auth/me", headers=headers_candidat).json()
    assert moi["status"] == "ACTIF"
    assert moi["must_change_password"] is False

    mes = client.get("/api/v1/candidatures/mes-candidatures", headers=headers_candidat).json()
    assert [c["titre_offre"] for c in mes] == ["Developpeur backend"]
    assert mes[0]["statut_candidature"] == "RECUE"


def test_candidature_publique_ne_remplace_pas_un_compte_existant(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)
    assert _postuler_public(client, offre["lien_token"]).status_code == 201

    seconde = _postuler_public(client, offre["lien_token"], email="AWA@exemple.ca")
    assert seconde.status_code == 409
    assert len(stockage.fichiers) == 1  # aucun fichier stocké pour la tentative refusée


def test_candidature_publique_piege_anti_robot_et_brouillon(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)
    robot = _postuler_public(client, offre["lien_token"], site_web="http://spam.test")
    assert robot.status_code == 201
    assert stockage.fichiers == {}

    brouillon = creer_offre(client, headers, status=False)
    assert client.get(f"/api/v1/public/offres/{brouillon['lien_token']}").status_code == 404
    assert _postuler_public(client, brouillon["lien_token"], email="b@exemple.ca").status_code == 404

    sans_consentement = _postuler_public(client, offre["lien_token"], email="c@exemple.ca", consentement_accepte="false")
    assert sans_consentement.status_code == 400


def test_fichiers_refuses(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)

    faux_zip = io.BytesIO()
    with zipfile.ZipFile(faux_zip, "w") as archive:
        archive.writestr("virus.txt", "pas un document word")
    cas = [
        ("cv.docx", faux_zip.getvalue(), DOCX_MIME),  # zip qui n'est pas un .docx
        ("cv.pdf", docx(), "application/pdf"),  # extension mensongère
        ("cv.exe", b"MZ....", "application/octet-stream"),
        ("cv.pdf", b"", "application/pdf"),
    ]
    for i, fichier in enumerate(cas):
        reponse = _postuler_public(client, offre["lien_token"], email=f"f{i}@exemple.ca",
                                   telephone=f"+1514555010{i}", fichier=fichier)
        assert reponse.status_code == 400, (fichier[0], reponse.text)
    assert stockage.fichiers == {}


def test_espace_candidat_depot_pdf_et_candidature(client, stockage, boite_mail):
    _, headers_recruteur = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers_recruteur)
    candidat, headers = compte(client, "CANDIDAT")

    sans_cv = client.post(f"/api/v1/candidatures/offres/{offre['lien_token']}", headers=headers)
    assert sans_cv.status_code == 400

    depot = client.post("/api/v1/cv/upload", files={"fichier": ("cv.pdf", pdf(), "application/pdf")}, headers=headers)
    assert depot.status_code == 200, depot.text
    assert "Python" in depot.json()["competences"]

    postule = client.post(f"/api/v1/candidatures/offres/{offre['lien_token']}", headers=headers)
    assert postule.status_code == 201
    assert client.post(f"/api/v1/candidatures/offres/{offre['lien_token']}", headers=headers).status_code == 400
    assert any("Candidature reçue" in m["subject"] for m in boite_mail.pour(candidat["email"]))

    lien = client.get("/api/v1/cv/moi/fichier", headers=headers)
    assert lien.status_code == 200


def test_remplacer_son_cv_efface_l_ancien_fichier_et_option_competences(client, stockage):
    _, headers = compte(client, "CANDIDAT")
    premier = client.post("/api/v1/cv/upload", files={"fichier": ("cv.docx", docx(), DOCX_MIME)}, headers=headers)
    ancien = next(iter(stockage.fichiers))
    client.put("/api/v1/cv/moi", json={"competences": ["Gestion de projet"]}, headers=headers)

    second = client.post(
        "/api/v1/cv/upload?maj_competences=false",
        files={"fichier": ("cv.pdf", pdf(), "application/pdf")},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["competences"] == ["Gestion de projet"]
    assert second.json()["code_cv"] == premier.json()["code_cv"]
    assert stockage.supprimes == [ancien]
    assert list(stockage.fichiers) != [ancien]


def test_shortlist_expliquee_tableau_de_bord_et_historique(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)
    creer_offre(client, headers, titre_offre="Offre sans candidature")

    # Awa coche Python + FastAPI (docx), Moussa ne coche rien.
    assert _postuler_public(client, offre["lien_token"]).status_code == 201
    assert _postuler_public(
        client, offre["lien_token"], email="moussa@exemple.ca", telephone="+15145550002", nom="Moussa Ba",
        fichier=("cv.docx", docx("Comptable avec dix ans d'experience en cabinet."), DOCX_MIME),
    ).status_code == 201

    resultats = client.get(f"/api/v1/offres/{offre['id_offre']}/resultats", headers=headers).json()
    assert [r["candidat"]["nom_prenom"] for r in resultats] == ["Awa Diop", "Moussa Ba"]
    premier, second = resultats
    assert premier["score_sim"] == 83.3
    assert premier["categorie"] == "good"
    assert [c["libelle"] for c in premier["ecarts"]] == ["Docker"]
    assert second["categorie"] == "low"
    assert second["recommendation"] == "Faible correspondance"
    assert "email" not in premier["candidat"]

    tableau = {o["titre_offre"]: o for o in client.get("/api/v1/offres/tableau-de-bord", headers=headers).json()}
    ligne = tableau["Developpeur backend"]
    assert ligne["nb_candidatures"] == 2
    assert ligne["categories"] == {"rec": 0, "good": 1, "review": 0, "low": 1}
    assert ligne["par_statut"] == {"RECUE": 2}
    assert tableau["Offre sans candidature"]["nb_candidatures"] == 0

    client.patch(f"/api/v1/offres/resultats/{premier['id_resultat']}/statut", json={"statut": "ENTRETIEN"},
                 headers=headers)
    historique = client.get(f"/api/v1/offres/resultats/{premier['id_resultat']}/historique", headers=headers).json()
    assert [(h["ancien_statut"], h["nouveau_statut"]) for h in historique] == [(None, "RECUE"), ("RECUE", "ENTRETIEN")]


def test_modifier_les_criteres_recalcule_les_scores(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)
    _postuler_public(client, offre["lien_token"])

    client.put(
        f"/api/v1/offres/{offre['id_offre']}",
        json={"criteres": [{"libelle": "Python", "niveau": "OBLIGATOIRE"}]},
        headers=headers,
    )
    resultat = client.get(f"/api/v1/offres/{offre['id_offre']}/resultats", headers=headers).json()[0]
    assert resultat["score_sim"] == 100.0
    assert resultat["categorie"] == "rec"


def test_matching_par_code_cv(client, stockage):
    _, headers_recruteur = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers_recruteur)
    _, headers_candidat = compte(client, "CANDIDAT")
    cv = client.post("/api/v1/cv/upload", files={"fichier": ("cv.docx", docx(), DOCX_MIME)},
                     headers=headers_candidat).json()

    reponse = client.post(
        "/api/v1/offres/matching",
        json={"code_cv": cv["code_cv"].lower(), "id_offre": offre["id_offre"]},
        headers=headers_recruteur,
    )
    assert reponse.status_code == 201, reponse.text
    assert reponse.json()["candidat"]["code_cv"] == cv["code_cv"]

    inconnu = client.post("/api/v1/offres/matching", json={"code_cv": "ZZZZZZZZ", "id_offre": offre["id_offre"]},
                          headers=headers_recruteur)
    assert inconnu.status_code == 404


def test_supprimer_une_offre_avec_candidatures(client, stockage):
    _, headers = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers)
    _postuler_public(client, offre["lien_token"])

    assert client.delete(f"/api/v1/offres/{offre['id_offre']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/offres/{offre['id_offre']}", headers=headers).status_code == 404


def test_supprimer_son_cv_efface_le_fichier_et_les_candidatures(client, stockage):
    _, headers_recruteur = compte(client, "RECRUTEUR")
    offre = creer_offre(client, headers_recruteur)
    _, headers = compte(client, "CANDIDAT")
    client.post("/api/v1/cv/upload", files={"fichier": ("cv.docx", docx(), DOCX_MIME)}, headers=headers)
    client.post(f"/api/v1/candidatures/offres/{offre['lien_token']}", headers=headers)
    fichier = next(iter(stockage.fichiers))

    assert client.delete("/api/v1/cv/moi", headers=headers).status_code == 204
    assert stockage.supprimes == [fichier]
    assert client.get("/api/v1/candidatures/mes-candidatures", headers=headers).json() == []
    assert client.get(f"/api/v1/offres/{offre['id_offre']}/resultats", headers=headers_recruteur).json() == []


def test_roles_etanches(client):
    _, headers_candidat = compte(client, "CANDIDAT")
    _, headers_recruteur = compte(client, "RECRUTEUR")

    assert client.post("/api/v1/offres/", json={"titre_offre": "Pirate"}, headers=headers_candidat).status_code == 403
    assert client.get("/api/v1/cv/moi", headers=headers_recruteur).status_code == 403
    assert client.get("/api/v1/candidatures/mes-candidatures", headers=headers_recruteur).status_code == 403
