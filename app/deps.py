"""
Dépendances FastAPI réutilisées par les routes.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models import Utilisateur, Recruteur, Candidat, MiniTypeUtilisateurEnum
from app.core.config import settings
from app.database import AsyncSessionLocal
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# L'API utilise SQLAlchemy asynchrone. La configuration reste la source unique
# de vérité; le pilote sync psycopg est converti pour les sessions async.
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Utilisateur:
    """
    Extrait et valide le token JWT pour retourner l'utilisateur connecté.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Impossible de valider les identifiants.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    if payload.get("type") != "access":
        raise credentials_exception

    # Récupération de l'utilisateur en BDD
    query = select(Utilisateur).where(Utilisateur.id_utilisateur == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user

async def get_current_recruteur(
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Recruteur:
    """
    Vérifie que l'utilisateur connecté est un recruteur et retourne son profil avec id_entreprise.
    """
    if current_user.type_utilisateur != MiniTypeUtilisateurEnum.recruteur:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seuls les recruteurs peuvent accéder à cette ressource."
        )

    query = select(Recruteur).where(Recruteur.id_utilisateur == current_user.id_utilisateur)
    result = await db.execute(query)
    recruteur = result.scalar_one_or_none()

    if not recruteur:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil recruteur introuvable."
        )

    return recruteur    



async def get_current_candidat(
    current_user: Utilisateur = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Candidat:
    """
    Vérifie que l'utilisateur connecté est un candidat et retourne son profil Candidat.
    """
    if current_user.type_utilisateur != MiniTypeUtilisateurEnum.candidat:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé uniquement aux candidats."
        )

    query = select(Candidat).where(Candidat.id_utilisateur == current_user.id_utilisateur)
    result = await db.execute(query)
    candidat = result.scalar_one_or_none()

    if not candidat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil candidat introuvable."
        )

    return candidat    
