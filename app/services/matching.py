import unicodedata

from app.models.critere_offre import CritereOffre, NiveauCritere
from app.models.cv import CV

POIDS_NIVEAU = {
    NiveauCritere.OBLIGATOIRE.value: 3,
    NiveauCritere.IMPORTANT.value: 2,
    NiveauCritere.SOUHAITABLE.value: 1,
}


def _normaliser(texte: str) -> str:
    texte = texte.lower().strip()
    texte = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in texte if not unicodedata.combining(c))


def _valeurs_texte(champ) -> list[str]:
    if isinstance(champ, list):
        return [str(v) for v in champ]
    if isinstance(champ, dict):
        return [str(v) for v in champ.values()]
    return []


def _texte_cv(cv: CV) -> str:
    morceaux: list[str] = []
    for champ in (cv.competences, cv.langues, cv.domaine_etude, cv.certifications):
        morceaux.extend(_valeurs_texte(champ))
    if cv.resume_cv:
        morceaux.append(cv.resume_cv)
    return _normaliser(" ".join(morceaux))


def calculer_score(cv: CV, criteres: list[CritereOffre]) -> float:
    """Score de correspondance CV/offre pondere par niveau de critere (JA-040).

    Recoupement de mots-cles : chaque critere est cherche comme sous-chaine
    dans le texte du CV (competences, langues, domaine d'etude, certifications,
    resume), insensible a la casse et aux accents. Ce n'est PAS une analyse
    semantique. Le vrai calcul vectoriel (cv_vector / offre_vector, deja
    prevu dans les modeles via pgvector) suppose un modele d'embedding
    externe qui n'est pas encore disponible (integration UjuzAI, JA-084/085).

    Renvoie 0.0 si l'offre n'a aucun critere (score provisoire, comme avant).
    """
    if not criteres:
        return 0.0

    texte_cv = _texte_cv(cv)
    poids_total = 0
    poids_obtenu = 0

    for critere in criteres:
        niveau = critere.niveau.value if hasattr(critere.niveau, "value") else critere.niveau
        poids = POIDS_NIVEAU.get(niveau, 1)
        poids_total += poids
        if _normaliser(critere.libelle) in texte_cv:
            poids_obtenu += poids

    if poids_total == 0:
        return 0.0
    return round(100 * poids_obtenu / poids_total, 1)
