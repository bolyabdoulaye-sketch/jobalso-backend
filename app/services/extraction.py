"""Extraction heuristique du contenu d'un CV (JA-031).

Ceci n'est PAS un moteur d'IA : c'est une extraction par mots-cles, en
attendant l'integration UjuzAI (E13). Elle ne remplit que ce qu'elle trouve
reellement dans le texte du document ("aucune donnee inventee", JA-033).
"""
import io

import pdfplumber
from docx import Document


class CVIllisibleError(Exception):
    """Leve quand le document ne peut pas etre lu ou ne contient aucun texte exploitable."""


COMPETENCES_CONNUES = [
    "python", "java", "javascript", "typescript", "php", "c++", "c#", "sql",
    "fastapi", "django", "flask", "react", "next.js", "vue", "angular",
    "node.js", "docker", "kubernetes", "postgresql", "mysql", "mongodb",
    "git", "linux", "excel", "power bi", "word", "powerpoint",
    "gestion de projet", "marketing", "comptabilite", "recrutement",
    "vente", "communication", "leadership", "aws", "azure", "gcp",
]

LANGUES_CONNUES = [
    "francais", "anglais", "espagnol", "arabe", "wolof", "portugais",
    "allemand", "italien", "mandarin", "chinois", "russe",
]


def _normaliser(texte: str) -> str:
    return texte.lower().replace("é", "e").replace("è", "e").replace("à", "a")


def extraire_texte_pdf(contenu: bytes) -> str:
    texte_pages = []
    with pdfplumber.open(io.BytesIO(contenu)) as pdf:
        for page in pdf.pages:
            texte_page = page.extract_text()
            if texte_page:
                texte_pages.append(texte_page)
    return "\n".join(texte_pages)


def extraire_texte_docx(contenu: bytes) -> str:
    document = Document(io.BytesIO(contenu))
    return "\n".join(p.text for p in document.paragraphs if p.text)


def detecter_mots_cles(texte_normalise: str, reference: list[str]) -> list[str]:
    trouves = []
    for mot in reference:
        if _normaliser(mot) in texte_normalise:
            trouves.append(mot.capitalize() if len(mot) > 3 else mot.upper())
    return trouves


def extraire_donnees_cv(contenu: bytes, extension: str) -> dict:
    """Retourne {resume_cv, competences, langues}. Leve CVIllisibleError si echec."""
    try:
        if extension == ".pdf":
            texte = extraire_texte_pdf(contenu)
        elif extension == ".docx":
            texte = extraire_texte_docx(contenu)
        else:
            raise CVIllisibleError("Format de fichier non pris en charge")
    except CVIllisibleError:
        raise
    except Exception as exc:
        raise CVIllisibleError(f"Impossible de lire le document : {exc}") from exc

    texte = texte.strip()
    if not texte or len(texte) < 20:
        raise CVIllisibleError("Le document ne contient pas de texte exploitable")

    texte_normalise = _normaliser(texte)
    competences = detecter_mots_cles(texte_normalise, COMPETENCES_CONNUES)
    langues = detecter_mots_cles(texte_normalise, LANGUES_CONNUES)

    # Resume : les 2000 premiers caracteres du texte brut extrait, faute de vrai resume genere par IA
    resume = texte[:2000]

    return {
        "resume_cv": resume,
        "competences": competences,
        "langues": langues,
    }
