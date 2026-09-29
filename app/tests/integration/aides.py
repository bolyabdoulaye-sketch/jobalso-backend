"""Aides communes aux tests d'intégration."""
import io
import uuid

from docx import Document

# ------------------------------------------------------------------
# Aides
# ------------------------------------------------------------------

_compteur = {"n": 0}


def _unique() -> int:
    _compteur["n"] += 1
    return _compteur["n"]


def inscrire(client, type_utilisateur="RECRUTEUR", email=None, **extra):
    n = _unique()
    email = email or f"user{n}-{uuid.uuid4().hex[:6]}@exemple.ca"
    donnees = {
        "email": email,
        "numero_telephone": f"+1514{n:07d}",
        "mot_de_passe": "MotDePasse123",
        "nom_prenom": f"Personne {n}",
        "type_utilisateur": type_utilisateur,
        "consentement_accepte": True,
        **extra,
    }
    reponse = client.post("/api/v1/auth/register", json=donnees)
    assert reponse.status_code == 201, reponse.text
    return {**donnees, **reponse.json()}


def connecter(client, email, mot_de_passe="MotDePasse123"):
    reponse = client.post("/api/v1/auth/login", data={"username": email, "password": mot_de_passe})
    assert reponse.status_code == 200, reponse.text
    return reponse.json()


def entetes(jetons):
    return {"Authorization": f"Bearer {jetons['access_token']}"}


def compte(client, type_utilisateur="RECRUTEUR", **extra):
    """Inscrit et connecte : retourne (infos, en-têtes d'authentification)."""
    infos = inscrire(client, type_utilisateur, **extra)
    return infos, entetes(connecter(client, infos["email"]))


def creer_offre(client, headers, **extra):
    donnees = {
        "titre_offre": "Developpeur backend",
        "criteres": [
            {"libelle": "Python", "niveau": "OBLIGATOIRE"},
            {"libelle": "FastAPI", "niveau": "IMPORTANT"},
            {"libelle": "Docker", "niveau": "SOUHAITABLE"},
        ],
        **extra,
    }
    reponse = client.post("/api/v1/offres/", json=donnees, headers=headers)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def docx(texte="Developpeur Python FastAPI avec cinq ans d'experience, francais et anglais."):
    document = Document()
    document.add_paragraph(texte)
    tampon = io.BytesIO()
    document.save(tampon)
    return tampon.getvalue()


def pdf(texte="Developpeuse Python FastAPI Docker, anglais courant"):
    """PDF minimal valide contenant une ligne de texte."""
    contenu = f"BT /F1 12 Tf 72 720 Td ({texte}) Tj ET".encode()
    objets = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(contenu)).encode() + b" >>\nstream\n" + contenu + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    sortie = bytearray(b"%PDF-1.4\n")
    positions = []
    for i, objet in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += f"{i} 0 obj\n".encode() + objet + b"\nendobj\n"
    debut_xref = len(sortie)
    sortie += f"xref\n0 {len(objets) + 1}\n0000000000 65535 f \n".encode()
    for position in positions:
        sortie += f"{position:010d} 00000 n \n".encode()
    sortie += f"trailer\n<< /Size {len(objets) + 1} /Root 1 0 R >>\nstartxref\n{debut_xref}\n%%EOF\n".encode()
    return bytes(sortie)


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
