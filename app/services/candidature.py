from sqlalchemy.orm import Session

from app.models.cv import CV
from app.models.historique_statut import HistoriqueStatutCandidature
from app.models.offre import Offre
from app.models.resultat import Resultat
from app.models.statut_candidature import StatutCandidature
from app.models.utilisateur import Utilisateur
from app.services.matching import calculer_score


def creer_candidature(db: Session, offre: Offre, cv: CV, auteur: Utilisateur) -> Resultat:
    """Crée la candidature (score + statut RECUE) et sa première entrée d'historique. Ne commit pas."""
    resultat = Resultat(
        id_offre=offre.id_offre,
        id_cv=cv.id_cv,
        score_sim=calculer_score(cv, offre.criteres),
        statut_candidature=StatutCandidature.RECUE.value,
    )
    db.add(resultat)
    db.flush()
    db.add(
        HistoriqueStatutCandidature(
            id_resultat=resultat.id_resultat,
            ancien_statut=None,
            nouveau_statut=StatutCandidature.RECUE.value,
            id_utilisateur=auteur.id_utilisateur,
        )
    )
    return resultat
