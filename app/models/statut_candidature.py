import enum


class StatutCandidature(str, enum.Enum):
    RECUE = "RECUE"
    EN_REVUE = "EN_REVUE"
    ENTRETIEN = "ENTRETIEN"
    DECISION = "DECISION"


LIBELLES_STATUT = {
    StatutCandidature.RECUE.value: "Candidature reçue",
    StatutCandidature.EN_REVUE.value: "En cours d'examen",
    StatutCandidature.ENTRETIEN.value: "Entretien",
    StatutCandidature.DECISION.value: "Décision prise",
}


def libelle_statut(statut: str | None) -> str:
    return LIBELLES_STATUT.get(statut or "", statut or "")
