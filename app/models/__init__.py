# Importe tous les modèles pour que SQLAlchemy (et Alembic) connaisse le schéma complet.
from app.models.utilisateur import Utilisateur, TypeUtilisateur, StatusUtilisateur  # noqa: F401
from app.models.candidat import Candidat  # noqa: F401
from app.models.recruteur import Recruteur  # noqa: F401
from app.models.cv import CV  # noqa: F401
from app.models.offre import Offre  # noqa: F401
from app.models.critere_offre import CritereOffre, NiveauCritere  # noqa: F401
from app.models.resultat import Resultat  # noqa: F401
from app.models.historique_statut import HistoriqueStatutCandidature  # noqa: F401
from app.models.organisation import Organisation  # noqa: F401
from app.models.membre_organisation import MembreOrganisation, RoleOrganisation  # noqa: F401
from app.models.invitation_organisation import (  # noqa: F401
    InvitationOrganisation,
    RoleInvitationOrganisation,
)
from app.models.session_utilisateur import SessionUtilisateur  # noqa: F401
