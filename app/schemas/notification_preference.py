import uuid
from datetime import datetime
from pydantic import BaseModel


class NotificationPreferenceRead(BaseModel):
    id: uuid.UUID
    utilisateur_id: uuid.UUID
    notifier_nouvelle_recommandation: bool
    notifier_candidature_recue: bool
    notifier_changement_etape: bool
    notifier_entrevue_proposee: bool
    notifier_candidature_refusee: bool
    notifier_recapitulatif_hebdo: bool
    notifier_rappel_profil: bool
    modifie_le: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    notifier_nouvelle_recommandation: bool | None = None
    notifier_candidature_recue: bool | None = None
    notifier_changement_etape: bool | None = None
    notifier_entrevue_proposee: bool | None = None
    notifier_candidature_refusee: bool | None = None
    notifier_recapitulatif_hebdo: bool | None = None
    notifier_rappel_profil: bool | None = None


class RecommendationDismissalCreate(BaseModel):
    poste_id: uuid.UUID