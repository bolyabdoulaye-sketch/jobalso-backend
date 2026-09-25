from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import get_db, get_current_user, get_current_recruteur
from app.models.database import Administrateur, Utilisateur, Candidat, Recruteur, MiniStatusUtilisateurEnum, MiniTypeUtilisateurEnum, Entreprise, SessionAuthentification
from app.schemas.auth import RefreshTokenRequest, UtilisateurCreate, UtilisateurRead, TokenResponse
from app.core.config import settings
from app.core.security import create_refresh_token, hash_password, hash_token, verify_password, create_access_token
from fastapi.security import OAuth2PasswordRequestForm
router = APIRouter(prefix="/auth", tags=["Authentification"])


def _refresh_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)


async def _create_session(db: AsyncSession, utilisateur: Utilisateur) -> str:
    refresh_token = create_refresh_token(utilisateur.id_utilisateur)
    db.add(
        SessionAuthentification(
            id_utilisateur=utilisateur.id_utilisateur,
            refresh_token_hash=hash_token(refresh_token),
            expire_le=_refresh_expiration(),
        )
    )
    return refresh_token


@router.post("/register", response_model=UtilisateurRead, status_code=status.HTTP_201_CREATED)
async def inscription(data: UtilisateurCreate, db: AsyncSession = Depends(get_db)):
    if data.type_utilisateur == MiniTypeUtilisateurEnum.recruteur:
        entreprise_fields = (data.nom_entreprise, data.pays, data.localisation_entreprise)
        if not all(value and value.strip() for value in entreprise_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Un recruteur doit fournir le nom, le pays et la localisation de l'entreprise.",
            )

    # 1. Vérifier si l'email existe déjà
    query = select(Utilisateur).where(Utilisateur.email == data.email)
    res = await db.execute(query)
    if res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Cet email est déjà utilisé."
        )

    # 2. Créer l'utilisateur de base
    nouvel_utilisateur = Utilisateur(
        email=data.email,
        numero_telephone=data.numero_telephone,
        mot_de_passe=hash_password(data.mot_de_passe),
        nom_prenom=data.nom_prenom,
        type_utilisateur=data.type_utilisateur,
        status=MiniStatusUtilisateurEnum.actif,
        must_change_password=False
    )
    db.add(nouvel_utilisateur)
    await db.flush()  # Récupère l'ID généré de l'utilisateur (id_utilisateur)

    # 3. Traitement selon le type d'utilisateur
    if data.type_utilisateur == MiniTypeUtilisateurEnum.candidat:
        candidat = Candidat(id_utilisateur=nouvel_utilisateur.id_utilisateur)
        db.add(candidat)

    elif data.type_utilisateur == MiniTypeUtilisateurEnum.administrateur:
        administrateur = Administrateur(id_utilisateur=nouvel_utilisateur.id_utilisateur)
        db.add(administrateur)

    elif data.type_utilisateur == MiniTypeUtilisateurEnum.recruteur:
        entreprise = None

        # Option B : Si un nom_entreprise a été fourni
        if data.nom_entreprise and data.pays and data.localisation_entreprise:
            nom_nettoye = data.nom_entreprise.strip()
            pays_nettoye= data.pays.strip()
            localisation_entreprise_nettoye=data.localisation_entreprise.strip()
            # Chercher si l'entreprise existe déjà (recherche insensible à la casse avec ilike si besoin)
            query_ent = select(Entreprise).where(Entreprise.nom_entreprise == nom_nettoye, Entreprise.pays== pays_nettoye, Entreprise.localisation_entreprise==localisation_entreprise_nettoye)
            res_ent = await db.execute(query_ent)
            entreprise = res_ent.scalar_one_or_none()

            # Si l'entreprise n'existe pas, on la crée
            if not entreprise:
                entreprise = Entreprise(nom_entreprise=nom_nettoye, pays=pays_nettoye, localisation_entreprise=localisation_entreprise_nettoye)
                db.add(entreprise)
                await db.flush()  # Récupère l'ID généré pour la nouvelle entreprise
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un recruteur doit obligatoirement fournir les infos sur l'entreprise"
            )

        # Création de l'entrée Recruteur avec l'id_entreprise
        recruteur = Recruteur(
            id_utilisateur=nouvel_utilisateur.id_utilisateur,
            id_entreprise=entreprise.id_entreprise  # Ajuste selon le nom de la clé primaire dans Entreprise (id ou id_entreprise)
        )
        db.add(recruteur)

    # 4. Validation finale de la transaction
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cet email ou ce numéro de téléphone est déjà utilisé.",
        )
    await db.refresh(nouvel_utilisateur)
    return nouvel_utilisateur


@router.post("/login", response_model=TokenResponse)
async def connexion(data: OAuth2PasswordRequestForm= Depends(), db: AsyncSession = Depends(get_db)):
    # 1. Récupérer l'utilisateur
    query = select(Utilisateur).where(Utilisateur.email == data.username)
    res = await db.execute(query)
    utilisateur = res.scalar_one_or_none()

    # 2. Vérifier le mot de passe
    if not utilisateur or not verify_password(data.password, utilisateur.mot_de_passe):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect."
        )

    if utilisateur.status != MiniStatusUtilisateurEnum.actif:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte n'est pas actif.",
        )

    # 3. Générer le Token JWT
    refresh_token = await _create_session(db, utilisateur)
    await db.commit()
    return {
        "access_token": create_access_token(utilisateur.id_utilisateur),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=TokenResponse)
async def rafraichir_jetons(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Fait tourner le refresh token et émet un nouvel access token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Refresh token invalide ou expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(data.refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "refresh":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    session_query = (
        select(SessionAuthentification)
        .where(
            SessionAuthentification.refresh_token_hash == hash_token(data.refresh_token),
            SessionAuthentification.revoque_le.is_(None),
            SessionAuthentification.expire_le > datetime.now(timezone.utc),
        )
        .with_for_update()
    )
    session = (await db.execute(session_query)).scalar_one_or_none()
    if session is None or str(session.id_utilisateur) != user_id:
        raise credentials_exception

    utilisateur = await db.get(Utilisateur, session.id_utilisateur)
    if utilisateur is None or utilisateur.status != MiniStatusUtilisateurEnum.actif:
        raise credentials_exception

    session.revoque_le = datetime.now(timezone.utc)
    new_refresh_token = await _create_session(db, utilisateur)
    await db.commit()
    return {
        "access_token": create_access_token(utilisateur.id_utilisateur),
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UtilisateurRead)
async def lire_mon_profil(
    current_user: Utilisateur = Depends(get_current_user)
):
    return current_user    
