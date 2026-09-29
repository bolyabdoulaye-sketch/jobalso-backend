import secrets
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import (
    get_db,
    get_current_membership,
    get_current_organisation,
    get_current_recruteur,
    require_role,
)
from app.core.rate_limit import check_rate_limit
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.recruteur import Recruteur
from app.models.candidat import Candidat
from app.models.offre import Offre
from app.models.critere_offre import CritereOffre
from app.models.cv import CV
from app.models.membre_organisation import MembreOrganisation, RoleOrganisation
from app.models.resultat import Resultat
from app.models.historique_statut import HistoriqueStatutCandidature
from app.models.statut_candidature import StatutCandidature
from app.models.organisation import Organisation
from app.schemas.offre import CategoriesCount, OffreCreate, OffreUpdate, OffreRead, OffreSynthese
from app.schemas.resultat import HistoriqueStatutRead, MatchingRequest, ResultatRead
from app.schemas.candidature import StatutUpdate
from app.services.matching import (
    SEUIL_A_EXAMINER,
    SEUIL_BON_MATCH,
    SEUIL_FORTEMENT_RECOMMANDE,
    calculer_score,
    explication_matching,
    recalculer_resultats_offre,
)


router = APIRouter(prefix="/offres", tags=["offres"])

# Collaboration (JA-008) : tout membre de l'organisation gère les offres de
# l'organisation (édition, shortlist, pipeline). Supprimer une offre reste
# réservé à son auteur ou à un ADMIN.


def generate_lien_token(db: Session) -> str:
    """Genere un token unique et non devinable pour le lien de candidature publique (JA-026)."""
    token = secrets.token_urlsafe(24)

    while db.query(Offre).filter(Offre.lien_token == token).first():
        token = secrets.token_urlsafe(24)

    return token


def offre_de_l_organisation(db: Session, offre_id: uuid.UUID, organisation: Organisation) -> Offre:
    offre = db.scalar(
        select(Offre).where(
            Offre.id_offre == offre_id,
            Offre.id_organisation == organisation.id_organisation,
        )
    )
    if not offre:
        raise HTTPException(status_code=404, detail="Offre introuvable")
    return offre


def _resultat_explique(resultat: Resultat, offre: Offre, cv: CV | None, nom_prenom: str | None) -> dict:
    evaluation = (
        explication_matching(cv, offre.criteres)
        if cv
        else {"recommendation": None, "categorie": None, "criteres_valides": [], "ecarts": []}
    )
    return {
        "id_resultat": resultat.id_resultat,
        "id_offre": resultat.id_offre,
        "id_cv": resultat.id_cv,
        "score_sim": resultat.score_sim,
        "statut_candidature": resultat.statut_candidature,
        "date_modification": resultat.date_modification,
        "recommendation": evaluation["recommendation"],
        "categorie": evaluation["categorie"],
        "criteres_valides": evaluation["criteres_valides"],
        "ecarts": evaluation["ecarts"],
        "candidat": (
            {
                "nom_prenom": nom_prenom or "",
                "localisation": cv.localisation,
                "type_poste_recherche": cv.type_poste_recherche,
                "competences": cv.competences,
                "langues": cv.langues,
                "code_cv": cv.code_cv,
            }
            if cv
            else None
        ),
    }


@router.post(
    "/",
    response_model=OffreRead,
    status_code=status.HTTP_201_CREATED,
)
def create_offre(
    offre_in: OffreCreate,
    recruteur: Recruteur = Depends(get_current_recruteur),
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    offre = Offre(
        id_recruteur=recruteur.id_recruteur,
        id_organisation=organisation.id_organisation,
        titre_offre=offre_in.titre_offre,
        description=offre_in.description,
        type_contrat=offre_in.type_contrat,
        revenu=offre_in.revenu,
        date_debut=offre_in.date_debut,
        date_fin=offre_in.date_fin,
        resume_offre=offre_in.resume_offre,
        status=offre_in.status,
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


@router.get(
    "/",
    response_model=list[OffreRead],
)
def list_my_offres(
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
    publiees: bool | None = Query(None, description="true : publiées, false : brouillons"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    requete = (
        select(Offre)
        .options(selectinload(Offre.criteres))
        .where(Offre.id_organisation == organisation.id_organisation)
    )
    if publiees is not None:
        requete = requete.where(Offre.status.is_(publiees))
    return db.scalars(
        requete.order_by(Offre.date_publication.desc()).limit(limit).offset(offset)
    ).all()


@router.get(
    "/tableau-de-bord",
    response_model=list[OffreSynthese],
)
def tableau_de_bord(
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    """Synthèse par offre : nombre de candidatures par catégorie et par statut."""
    score = Resultat.score_sim
    # Sans critère, le moteur classe tout « À examiner » : même règle ici.
    avec_criteres = select(CritereOffre.id_critere).where(CritereOffre.id_offre == Offre.id_offre).exists()
    candidature = Resultat.id_resultat.is_not(None)
    lignes = db.execute(
        select(
            Offre.id_offre,
            Offre.titre_offre,
            Offre.status,
            Offre.date_publication,
            func.count(Resultat.id_resultat),
            func.count(case((avec_criteres & (score >= SEUIL_FORTEMENT_RECOMMANDE), 1))),
            func.count(case((avec_criteres & (score >= SEUIL_BON_MATCH) & (score < SEUIL_FORTEMENT_RECOMMANDE), 1))),
            func.count(
                case(
                    (
                        (candidature & ~avec_criteres)
                        | (avec_criteres & (score >= SEUIL_A_EXAMINER) & (score < SEUIL_BON_MATCH)),
                        1,
                    )
                )
            ),
            func.count(case((avec_criteres & (score < SEUIL_A_EXAMINER), 1))),
        )
        .outerjoin(Resultat, Resultat.id_offre == Offre.id_offre)
        .where(Offre.id_organisation == organisation.id_organisation)
        .group_by(Offre.id_offre)
        .order_by(Offre.date_publication.desc())
    ).all()

    statuts = db.execute(
        select(Resultat.id_offre, Resultat.statut_candidature, func.count())
        .join(Offre, Offre.id_offre == Resultat.id_offre)
        .where(Offre.id_organisation == organisation.id_organisation)
        .group_by(Resultat.id_offre, Resultat.statut_candidature)
    ).all()
    par_offre: dict[uuid.UUID, dict[str, int]] = {}
    for id_offre, statut, nombre in statuts:
        par_offre.setdefault(id_offre, {})[statut or "INCONNU"] = nombre

    return [
        OffreSynthese(
            id_offre=id_offre,
            titre_offre=titre,
            status=publiee,
            date_publication=date_publication,
            nb_candidatures=total,
            categories=CategoriesCount(rec=rec, good=good, review=review, low=low),
            par_statut=par_offre.get(id_offre, {}),
        )
        for id_offre, titre, publiee, date_publication, total, rec, good, review, low in lignes
    ]


@router.get(
    "/{offre_id}",
    response_model=OffreRead,
)
def get_offre(
    offre_id: uuid.UUID,
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    return offre_de_l_organisation(db, offre_id, organisation)


@router.put(
    "/{offre_id}",
    response_model=OffreRead,
)
def update_offre(
    offre_id: uuid.UUID,
    offre_in: OffreUpdate,
    background_tasks: BackgroundTasks,
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    offre = offre_de_l_organisation(db, offre_id, organisation)

    data = offre_in.model_dump(exclude_unset=True)
    criteres = data.pop("criteres", None)

    for field, value in data.items():
        if field in ("titre_offre", "status") and value is None:
            continue  # champs obligatoires en base
        setattr(offre, field, value)

    criteres_modifies = criteres is not None

    if criteres_modifies:
        offre.criteres.clear()

        for critere in criteres:
            db.add(
                CritereOffre(
                    id_offre=offre.id_offre,
                    libelle=critere["libelle"],
                    niveau=critere["niveau"],
                )
            )

    db.commit()
    db.refresh(offre)

    # JA-044 : recalcul asynchrone après modification des critères du poste.
    if criteres_modifies:
        background_tasks.add_task(
            recalculer_resultats_offre,
            offre.id_offre,
        )

    return offre


@router.delete(
    "/{offre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_offre(
    offre_id: uuid.UUID,
    recruteur: Recruteur = Depends(get_current_recruteur),
    membership: MembreOrganisation = Depends(get_current_membership),
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    """Supprime l'offre, ses critères, ses candidatures et leur historique."""
    offre = offre_de_l_organisation(db, offre_id, organisation)

    if offre.id_recruteur != recruteur.id_recruteur and membership.role != RoleOrganisation.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Seul l'auteur de l'offre ou un administrateur peut la supprimer",
        )

    db.delete(offre)
    db.commit()


@router.post(
    "/matching",
    response_model=ResultatRead,
    status_code=status.HTTP_201_CREATED,
)
def match_cv_to_offre(
    matching_in: MatchingRequest,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    """Ajoute à une offre le CV dont le candidat a communiqué son code."""
    # Le code CV est court : on borne les essais pour empêcher de les deviner.
    check_rate_limit(f"matching:{current_user.id_utilisateur}", 30, 600)

    offre = offre_de_l_organisation(db, matching_in.id_offre, organisation)

    cv = db.scalar(select(CV).where(CV.code_cv == matching_in.code_cv.strip().upper()))

    if not cv:
        raise HTTPException(
            status_code=404,
            detail="Aucun CV trouve avec ce code",
        )

    existing = db.scalar(
        select(Resultat).where(
            Resultat.id_offre == offre.id_offre,
            Resultat.id_cv == cv.id_cv,
        )
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Ce CV a deja ete evalue pour cette offre",
        )

    # Score reel pondere par niveau de critere (JA-018/019/040).
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

    nom = db.scalar(
        select(Utilisateur.nom_prenom)
        .join(Candidat, Candidat.id_utilisateur == Utilisateur.id_utilisateur)
        .where(Candidat.id_candidat == cv.id_candidat)
    )
    return _resultat_explique(resultat, offre, cv, nom)


@router.get(
    "/{offre_id}/resultats",
    response_model=list[ResultatRead],
)
def list_matching_results(
    offre_id: uuid.UUID,
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Shortlist expliquée : candidatures triées par score, avec l'aperçu du candidat."""
    offre = offre_de_l_organisation(db, offre_id, organisation)

    # Une seule requête pour les candidatures, les CV et les noms (pas de N+1).
    lignes = db.execute(
        select(Resultat, CV, Utilisateur.nom_prenom)
        .join(CV, CV.id_cv == Resultat.id_cv)
        .join(Candidat, Candidat.id_candidat == CV.id_candidat)
        .join(Utilisateur, Utilisateur.id_utilisateur == Candidat.id_utilisateur)
        .where(Resultat.id_offre == offre.id_offre)
        .order_by(Resultat.score_sim.desc(), Resultat.date_modification.asc())
        .limit(limit)
        .offset(offset)
    ).all()

    return [_resultat_explique(resultat, offre, cv, nom) for resultat, cv, nom in lignes]


def _resultat_de_l_organisation(db: Session, resultat_id: uuid.UUID, organisation: Organisation) -> Resultat:
    resultat = db.scalar(
        select(Resultat)
        .join(Offre, Offre.id_offre == Resultat.id_offre)
        .where(
            Resultat.id_resultat == resultat_id,
            Offre.id_organisation == organisation.id_organisation,
        )
    )
    if not resultat:
        raise HTTPException(status_code=404, detail="Candidature introuvable")
    return resultat


# Changement de statut d'une candidature par le recruteur (JA-056)
@router.patch(
    "/resultats/{resultat_id}/statut",
    response_model=ResultatRead,
)
def update_statut_candidature(
    resultat_id: uuid.UUID,
    statut_in: StatutUpdate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    resultat = _resultat_de_l_organisation(db, resultat_id, organisation)

    nouveau = statut_in.statut.value
    ancien = resultat.statut_candidature

    if ancien == nouveau:
        raise HTTPException(
            status_code=400,
            detail="La candidature est deja a ce statut",
        )

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

    return resultat


@router.get(
    "/resultats/{resultat_id}/historique",
    response_model=list[HistoriqueStatutRead],
)
def historique_candidature(
    resultat_id: uuid.UUID,
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    resultat = _resultat_de_l_organisation(db, resultat_id, organisation)
    return db.scalars(
        select(HistoriqueStatutCandidature)
        .where(HistoriqueStatutCandidature.id_resultat == resultat.id_resultat)
        .order_by(HistoriqueStatutCandidature.date_changement.asc())
    ).all()
