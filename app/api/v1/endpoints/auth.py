from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)
from app.models.utilisateur import (
    Utilisateur,
    TypeUtilisateur,
    StatusUtilisateur,
)
from app.models.candidat import Candidat
from app.models.recruteur import Recruteur
from app.schemas.utilisateur import (
    UtilisateurCreate,
    UtilisateurRead,
    PersonaRecruteurRequest,
)


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# Version courante de la politique de confidentialité.
POLITIQUE_CONFIDENTIALITE_VERSION = "1.0"


PERSONAS_RECRUTEUR_AUTORISEES = {
    "pme",
    "entrepreneur",
    "rh",
    "recruteur",
    "gestionnaire",
}


@router.post(
    "/register",
    response_model=UtilisateurRead,
    status_code=status.HTTP_201_CREATED,
)
def register(
    user_in: UtilisateurCreate,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.email == user_in.email
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email deja utilise",
        )

    existing_phone = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.numero_telephone
            == user_in.numero_telephone
        )
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=400,
            detail="Numero de telephone deja utilise",
        )

    if not user_in.consentement_accepte:
        raise HTTPException(
            status_code=400,
            detail=(
                "Vous devez accepter la politique de "
                "confidentialite pour creer un compte"
            ),
        )

    if (
        user_in.type_utilisateur
        == TypeUtilisateur.CANDIDAT
        and user_in.persona is not None
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Un compte candidat ne peut pas definir "
                "de persona recruteur."
            ),
        )

    if (
        user_in.type_utilisateur
        == TypeUtilisateur.RECRUTEUR
        and user_in.persona is not None
        and user_in.persona
        not in PERSONAS_RECRUTEUR_AUTORISEES
    ):
        raise HTTPException(
            status_code=400,
            detail="Persona recruteur invalide.",
        )

    utilisateur = Utilisateur(
        email=user_in.email,
        numero_telephone=user_in.numero_telephone,
        mot_de_passe=hash_password(
            user_in.mot_de_passe
        ),
        nom_prenom=user_in.nom_prenom,
        type_utilisateur=user_in.type_utilisateur,
        status=StatusUtilisateur.EN_ATTENTE,
        consentement_accepte=True,
        consentement_date=datetime.utcnow(),
        consentement_version=(
            POLITIQUE_CONFIDENTIALITE_VERSION
        ),
    )

    db.add(utilisateur)
    db.flush()

    if (
        user_in.type_utilisateur
        == TypeUtilisateur.CANDIDAT
    ):
        candidat = Candidat(
            id_utilisateur=(
                utilisateur.id_utilisateur
            )
        )

        db.add(candidat)

    elif (
        user_in.type_utilisateur
        == TypeUtilisateur.RECRUTEUR
    ):
        recruteur = Recruteur(
            id_utilisateur=(
                utilisateur.id_utilisateur
            ),
            persona=user_in.persona,
        )

        db.add(recruteur)

    else:
        raise HTTPException(
            status_code=400,
            detail="Type d'utilisateur invalide",
        )

    db.commit()
    db.refresh(utilisateur)

    return utilisateur


@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Connexion centrale Jobalso.

    L'utilisateur fournit :
    - email
    - mot de passe

    Le type de compte est déterminé automatiquement
    à partir du compte trouvé en base.

    Le champ OAuth2 "scope" reste accepté lorsqu'il est
    fourni depuis un parcours contextualisé, afin de
    conserver l'isolation stricte candidat/recruteur.
    """

    utilisateur = (
        db.query(Utilisateur)
        .filter(
            Utilisateur.email
            == form_data.username
        )
        .first()
    )

    if not utilisateur or not verify_password(
        form_data.password,
        utilisateur.mot_de_passe,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if (
        utilisateur.status
        == StatusUtilisateur.SUPPRIME
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte supprime",
        )

    if (
        utilisateur.status
        == StatusUtilisateur.INACTIF
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte inactif",
        )

    # ---------------------------------------------------------
    # ROLE AUTOMATIQUE
    # ---------------------------------------------------------

    role_compte = (
        "candidat"
        if utilisateur.type_utilisateur
        == TypeUtilisateur.CANDIDAT
        else "recruteur"
        if utilisateur.type_utilisateur
        == TypeUtilisateur.RECRUTEUR
        else None
    )

    if role_compte is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Type de compte non reconnu.",
        )

    # ---------------------------------------------------------
    # ROLE CONTEXTUEL OPTIONNEL
    # ---------------------------------------------------------

    scopes = form_data.scopes or []

    if len(scopes) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Espace de connexion invalide.",
        )

    if len(scopes) == 1:
        role_demande = (
            scopes[0].strip().lower()
        )

        if role_demande not in {
            "candidat",
            "recruteur",
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Espace de connexion invalide.",
            )

        if role_demande != role_compte:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Ces identifiants ne correspondent "
                    "pas a cet espace."
                ),
            )

    # ---------------------------------------------------------
    # TOKEN
    # ---------------------------------------------------------

    access_token = create_access_token(
        subject=str(
            utilisateur.id_utilisateur
        )
    )

    persona = None

    if (
        utilisateur.type_utilisateur
        == TypeUtilisateur.RECRUTEUR
    ):
        recruteur = (
            db.query(Recruteur)
            .filter(
                Recruteur.id_utilisateur
                == utilisateur.id_utilisateur
            )
            .first()
        )

        if recruteur is not None:
            persona = recruteur.persona

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "type_utilisateur": (
            utilisateur
            .type_utilisateur
            .value
        ),
        "persona": persona,
    }


@router.post("/persona")
def save_recruiter_persona(
    data: PersonaRecruteurRequest,
    current_user: Utilisateur = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    if (
        current_user.type_utilisateur
        != TypeUtilisateur.RECRUTEUR
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Seul un recruteur peut définir "
                "un persona recruteur."
            ),
        )

    persona = data.persona.strip().lower()

    if persona not in PERSONAS_RECRUTEUR_AUTORISEES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona recruteur invalide.",
        )

    recruteur = (
        db.query(Recruteur)
        .filter(
            Recruteur.id_utilisateur
            == current_user.id_utilisateur
        )
        .first()
    )

    if recruteur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil recruteur introuvable.",
        )

    recruteur.persona = persona

    db.commit()
    db.refresh(recruteur)

    return {
        "persona": recruteur.persona
    }


@router.get(
    "/me",
    response_model=UtilisateurRead,
)
def read_current_user(
    current_user: Utilisateur = Depends(
        get_current_user
    ),
    db: Session = Depends(get_db),
):
    persona = None

    if (
        current_user.type_utilisateur
        == TypeUtilisateur.RECRUTEUR
    ):
        recruteur = (
            db.query(Recruteur)
            .filter(
                Recruteur.id_utilisateur
                == current_user.id_utilisateur
            )
            .first()
        )

        if recruteur is not None:
            persona = recruteur.persona

    result = UtilisateurRead.model_validate(
        current_user
    )

    result.persona = persona

    return result