import secrets
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_role
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.recruteur import Recruteur
from app.models.candidat import Candidat
from app.models.offre import Offre
from app.models.critere_offre import CritereOffre
from app.models.cv import CV
from app.models.resultat import Resultat
from app.models.historique_statut import HistoriqueStatutCandidature
from app.models.statut_candidature import StatutCandidature, libelle_statut
from app.schemas.offre import OffreCreate, OffreUpdate, OffreRead
from app.schemas.resultat import MatchingRequest, ResultatRead
from app.schemas.candidature import StatutUpdate
from app.services.email import send_notification_email
from app.services.matching import calculer_score

router = APIRouter(prefix="/offres", tags=["offres"])


def get_own_recruteur(current_user: Utilisateur, db: Session) -> Recruteur:
    recruteur = db.query(Recruteur).filter(Recruteur.id_utilisateur == current_user.id_utilisateur).first()
    if not recruteur:
        raise HTTPException(status_code=404, detail="Profil recruteur introuvable")
    return recruteur


def generate_lien_token(db: Session) -> str:
    """Genere un token unique et non devinable pour le lien de candidature publique (JA-026)."""
    token = secrets.token_urlsafe(24)
    while db.query(Offre).filter(Offre.lien_token == token).first():
        token = secrets.token_urlsafe(24)
    return token


@router.post("/", response_model=OffreRead, status_code=status.HTTP_201_CREATED)
def create_offre(
    offre_in: OffreCreate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)

    offre = Offre(
        id_recruteur=recruteur.id_recruteur,
        titre_offre=offre_in.titre_offre,
        description=offre_in.description,
        type_contrat=offre_in.type_contrat,
        revenu=offre_in.revenu,
        date_debut=offre_in.date_debut,
        date_fin=offre_in.date_fin,
        resume_offre=offre_in.resume_offre,
        status=True,
        lien_token=generate_lien_token(db),
    )
    db.add(offre)
    db.flush()

    # Hierarchisation des criteres (JA-018/019)
    for critere_in in offre_in.criteres:
        db.add(
            CritereOffre(
                id_offre=offre.id_offre,
                libelle=critere_in.libelle,
                niveau=critere_in.niveau,
            )
        )

    db.commit()
    db.refresh(offre)
    return offre


@router.get("/", response_model=list[OffreRead])
def list_my_offres(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    return db.query(Offre).filter(Offre.id_recruteur == recruteur.id_recruteur).all()


@router.get("/{offre_id}", response_model=OffreRead)
def get_offre(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return offre


@router.put("/{offre_id}", response_model=OffreRead)
def update_offre(
    offre_id: uuid.UUID,
    offre_in: OffreUpdate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    for field, value in offre_in.model_dump(exclude_unset=True).items():
        setattr(offre, field, value)

    db.commit()
    db.refresh(offre)
    return offre


@router.delete("/{offre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_offre(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    db.delete(offre)
    db.commit()


@router.post("/matching", response_model=ResultatRead, status_code=status.HTTP_201_CREATED)
def match_cv_to_offre(
    matching_in: MatchingRequest,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)

    offre = db.query(Offre).filter(Offre.id_offre == matching_in.id_offre).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    cv = db.query(CV).filter(CV.code_cv == matching_in.code_cv.upper()).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve avec ce code")

    existing = db.query(Resultat).filter(
        Resultat.id_offre == offre.id_offre, Resultat.id_cv == cv.id_cv
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce CV a deja ete evalue pour cette offre")

    # Score reel pondere par niveau de critere (JA-018/019/040). Renvoie 0.0
    # si l'offre n'a aucun critere defini (comportement provisoire inchange).
    score = calculer_score(cv, offre.criteres)

    resultat = Resultat(
        id_offre=offre.id_offre,
        id_cv=cv.id_cv,
        score_sim=score,
        statut_candidature=StatutCandidature.RECUE.value,
    )
    db.add(resultat)
    db.flush()

    # Premiere entree de l'historique du pipeline (JA-056)
    db.add(
        HistoriqueStatutCandidature(
            id_resultat=resultat.id_resultat,
            ancien_statut=None,
            nouveau_statut=StatutCandidature.RECUE.value,
            id_utilisateur=current_user.id_utilisateur,
        )
    )
    db.commit()
    db.refresh(resultat)
    return resultat


@router.get("/{offre_id}/resultats", response_model=list[ResultatRead])
def list_matching_results(
    offre_id: uuid.UUID,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)
    offre = db.query(Offre).filter(Offre.id_offre == offre_id).first()
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    if offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    return db.query(Resultat).filter(Resultat.id_offre == offre_id).order_by(
        Resultat.score_sim.desc()
    ).all()


# Changement de statut d'une candidature par le recruteur (JA-056) + notification (JA-057)
@router.patch("/resultats/{resultat_id}/statut", response_model=ResultatRead)
def update_statut_candidature(
    resultat_id: uuid.UUID,
    statut_in: StatutUpdate,
    background_tasks: BackgroundTasks,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    recruteur = get_own_recruteur(current_user, db)

    resultat = db.query(Resultat).filter(Resultat.id_resultat == resultat_id).first()
    if not resultat:
        raise HTTPException(status_code=404, detail="Candidature introuvable")

    offre = db.query(Offre).filter(Offre.id_offre == resultat.id_offre).first()
    if not offre or offre.id_recruteur != recruteur.id_recruteur:
        raise HTTPException(status_code=403, detail="Acces refuse")

    nouveau = statut_in.statut.value
    ancien = resultat.statut_candidature
    if ancien == nouveau:
        raise HTTPException(status_code=400, detail="La candidature est deja a ce statut")

    resultat.statut_candidature = nouveau
    db.add(
        HistoriqueStatutCandidature(
            id_resultat=resultat.id_resultat,
            ancien_statut=ancien,
            nouveau_statut=nouveau,
            id_utilisateur=current_user.id_utilisateur,
        )
    )
    db.commit()
    db.refresh(resultat)

    # Notification du candidat (respecte son desabonnement)
    cv = db.query(CV).filter(CV.id_cv == resultat.id_cv).first()
    candidat = db.query(Candidat).filter(Candidat.id_candidat == cv.id_candidat).first() if cv else None
    destinataire = (
        db.query(Utilisateur).filter(Utilisateur.id_utilisateur == candidat.id_utilisateur).first()
        if candidat
        else None
    )
    if destinataire:
        # Copie simple : la session sera fermee quand la tache de fond s'executera
        dest = SimpleNamespace(
            email=destinataire.email,
            id_utilisateur=destinataire.id_utilisateur,
            notifications_email=destinataire.notifications_email,
        )
        libelle = libelle_statut(nouveau)
        background_tasks.add_task(
            send_notification_email,
            dest,
            "Mise a jour de votre candidature",
            f"Bonjour,\n\nLe statut de votre candidature pour « {offre.titre_offre} » a change : {libelle}.",
            f"<p>Bonjour,</p><p>Le statut de votre candidature pour « {offre.titre_offre} » "
            f"a change : <strong>{libelle}</strong>.</p>",
        )

    return resultat
