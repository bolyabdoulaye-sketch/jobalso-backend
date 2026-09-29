import unicodedata

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.critere_offre import CritereOffre, NiveauCritere
from app.models.cv import CV
from app.models.offre import Offre
from app.models.resultat import Resultat

POIDS_NIVEAU = {
    NiveauCritere.OBLIGATOIRE.value: 3,
    NiveauCritere.IMPORTANT.value: 2,
    NiveauCritere.SOUHAITABLE.value: 1,
}

# JA-042 — seuils documentés et stables.
SEUIL_FORTEMENT_RECOMMANDE = 88.0
SEUIL_BON_MATCH = 72.0
SEUIL_A_EXAMINER = 50.0

# JA-040 — un critère obligatoire manquant empêche un profil d'atteindre
# les catégories "Bons matchs" et "Fortement recommandéss".
PLAFOND_MANDATOIRE_MANQUANT = SEUIL_BON_MATCH - 0.1


def _normaliser(texte: str) -> str:
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c))


def _valeurs_texte(champ) -> list[str]:
    if isinstance(champ, list):
        return [str(v) for v in champ]
    if isinstance(champ, dict):
        return [str(v) for v in champ.values()]
    if champ not in (None, ""):
        return [str(champ)]
    return []


def _texte_cv(cv: CV) -> str:
    morceaux: list[str] = []
    for champ in (
        cv.competences,
        cv.langues,
        cv.domaine_etude,
        cv.certifications,
        cv.experience,
        cv.education,
        cv.localisation,
        cv.type_poste_recherche,
    ):
        morceaux.extend(_valeurs_texte(champ))
    if cv.resume_cv:
        morceaux.append(cv.resume_cv)
    return _normaliser(" ".join(morceaux))


def _niveau(critere: CritereOffre) -> str:
    return critere.niveau.value if hasattr(critere.niveau, "value") else str(critere.niveau)


def _critere_rempli(critere: CritereOffre, texte_cv: str) -> bool:
    libelle = _normaliser(critere.libelle)
    return bool(libelle) and libelle in texte_cv


def evaluer_matching(cv: CV, criteres: list[CritereOffre]) -> dict:
    """Calcule le matching déterministe et son explication (JA-039 à JA-042).

    Le score est une moyenne pondérée par niveau. Un obligatoire manquant
    plafonne le score à 71,9 %, afin qu'il ne puisse pas être classé
    "Bons matchs" ou "Fortement recommandéss".
    """
    if not criteres:
        return {
            "score": 0.0,
            "recommendation": "À examiner",
            "criteres_valides": [],
            "ecarts": [],
            "obligatoires_manquants": [],
        }

    texte_cv = _texte_cv(cv)
    poids_total = 0
    poids_obtenu = 0
    criteres_valides = []
    ecarts = []
    obligatoires_manquants = []

    for critere in criteres:
        niveau = _niveau(critere)
        poids = POIDS_NIVEAU.get(niveau, POIDS_NIVEAU[NiveauCritere.IMPORTANT.value])
        poids_total += poids
        item = {"libelle": critere.libelle, "niveau": niveau}
        if _critere_rempli(critere, texte_cv):
            poids_obtenu += poids
            criteres_valides.append(item)
        else:
            ecarts.append(item)
            if niveau == NiveauCritere.OBLIGATOIRE.value:
                obligatoires_manquants.append(item)

    score = round(100 * poids_obtenu / poids_total, 1) if poids_total else 0.0
    if obligatoires_manquants:
        score = min(score, PLAFOND_MANDATOIRE_MANQUANT)

    if score >= SEUIL_FORTEMENT_RECOMMANDE:
        recommendation = "Fortement recommandés"
    elif score >= SEUIL_BON_MATCH:
        recommendation = "Bons matchs"
    else:
        recommendation = "À examiner"

    return {
        "score": score,
        "recommendation": recommendation,
        "criteres_valides": criteres_valides,
        "ecarts": ecarts,
        "obligatoires_manquants": obligatoires_manquants,
    }


def calculer_score(cv: CV, criteres: list[CritereOffre]) -> float:
    """Compatibilité 0–100, conservée pour les appels existants."""
    return evaluer_matching(cv, criteres)["score"]


def explication_matching(cv: CV, criteres: list[CritereOffre]) -> dict:
    return evaluer_matching(cv, criteres)


def recalculer_resultats_offre(offre_id, db: Session | None = None) -> None:
    """JA-044 : recalcul idempotent de tous les résultats d'une offre."""
    own_session = db is None
    session = db or SessionLocal()
    try:
        offre = session.query(Offre).filter(Offre.id_offre == offre_id).first()
        if not offre:
            return
        resultats = session.query(Resultat).filter(Resultat.id_offre == offre.id_offre).all()
        for resultat in resultats:
            cv = session.query(CV).filter(CV.id_cv == resultat.id_cv).first()
            if cv:
                resultat.score_sim = calculer_score(cv, offre.criteres)
        session.commit()
    finally:
        if own_session:
            session.close()


def recalculer_resultats_cv(cv_id, db: Session | None = None) -> None:
    """JA-044 : recalcul idempotent après modification d'un profil/CV."""
    own_session = db is None
    session = db or SessionLocal()
    try:
        cv = session.query(CV).filter(CV.id_cv == cv_id).first()
        if not cv:
            return
        resultats = session.query(Resultat).filter(Resultat.id_cv == cv.id_cv).all()
        for resultat in resultats:
            offre = session.query(Offre).filter(Offre.id_offre == resultat.id_offre).first()
            if offre:
                resultat.score_sim = calculer_score(cv, offre.criteres)
        session.commit()
    finally:
        if own_session:
            session.close()
