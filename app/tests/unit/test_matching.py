import sys
import types

# Le projet utilise pgvector côté production ; le module n'est pas nécessaire
# pour tester la logique déterministe du moteur.
try:
    import pgvector.sqlalchemy  # noqa: F401  (vrai module : les tests d'intégration en ont besoin)
except ImportError:
    pgvector = types.ModuleType("pgvector")
    pgvector_sqlalchemy = types.ModuleType("pgvector.sqlalchemy")
    from sqlalchemy import JSON
    pgvector_sqlalchemy.Vector = lambda *args, **kwargs: JSON()
    pgvector.sqlalchemy = pgvector_sqlalchemy
    sys.modules["pgvector"] = pgvector
    sys.modules["pgvector.sqlalchemy"] = pgvector_sqlalchemy

from app.models.critere_offre import CritereOffre, NiveauCritere
from app.models.candidat import Candidat
from app.models.offre import Offre
from app.models.recruteur import Recruteur
from app.models.resultat import Resultat
from app.models.statut_candidature import StatutCandidature
from app.models.utilisateur import Utilisateur
from app.models.cv import CV
from app.services.matching import (
    PLAFOND_MANDATOIRE_MANQUANT,
    SEUIL_BON_MATCH,
    evaluer_matching,
    recalculer_resultats_cv,
    recalculer_resultats_offre,
)


def cv(**kwargs):
    base = dict(
        resume_cv="Développeur Python senior",
        experience=["5 ans Python"],
        education=["Informatique"],
        langues=["Français", "Anglais"],
        domaine_etude=["Informatique"],
        competences=["Python", "FastAPI", "PostgreSQL"],
        certifications=[],
        localisation="Dakar",
        type_poste_recherche="Développeur backend",
    )
    base.update(kwargs)
    return CV(**base)


def critere(libelle, niveau):
    return CritereOffre(libelle=libelle, niveau=niveau)


def test_ja039_score_0_100_et_deterministe():
    criteres = [
        critere("Python", NiveauCritere.OBLIGATOIRE),
        critere("FastAPI", NiveauCritere.IMPORTANT),
        critere("Docker", NiveauCritere.SOUHAITABLE),
    ]
    a = evaluer_matching(cv(), criteres)
    b = evaluer_matching(cv(), criteres)

    assert 0 <= a["score"] <= 100
    assert a["score"] == b["score"]
    assert a["score"] == 83.3  # 5/6 du poids total


def test_ja040_obligatoire_manquant_plafonne_le_score():
    result = evaluer_matching(
        cv(),
        [
            critere("Docker", NiveauCritere.OBLIGATOIRE),
            *[critere(skill, NiveauCritere.SOUHAITABLE) for skill in [
                "Python", "FastAPI", "PostgreSQL", "Français", "Anglais",
                "Informatique", "Dakar", "Développeur backend", "5 ans Python", "senior"
            ]],
        ],
    )

    assert result["obligatoires_manquants"][0]["libelle"] == "Docker"
    assert result["score"] == PLAFOND_MANDATOIRE_MANQUANT
    assert result["score"] < SEUIL_BON_MATCH


def test_ja041_explicabilite_criteres_valides_et_ecarts():
    result = evaluer_matching(
        cv(),
        [
            critere("Python", NiveauCritere.OBLIGATOIRE),
            critere("Docker", NiveauCritere.IMPORTANT),
            critere("Anglais", NiveauCritere.SOUHAITABLE),
        ],
    )

    assert [x["libelle"] for x in result["criteres_valides"]] == ["Python", "Anglais"]
    assert [x["libelle"] for x in result["ecarts"]] == ["Docker"]
    assert result["recommendation"] == "À examiner"


def test_ja042_tiers_documentes():
    fort = evaluer_matching(cv(), [critere("Python", NiveauCritere.OBLIGATOIRE)])
    bon = evaluer_matching(cv(), [critere("Python", NiveauCritere.OBLIGATOIRE), critere("Docker", NiveauCritere.SOUHAITABLE)])
    examine = evaluer_matching(cv(), [critere("Python", NiveauCritere.IMPORTANT), critere("Docker", NiveauCritere.IMPORTANT)])
    faible = evaluer_matching(cv(), [critere("Docker", NiveauCritere.IMPORTANT), critere("Java", NiveauCritere.IMPORTANT)])

    assert fort["recommendation"] == "Fortement recommandés"
    assert bon["recommendation"] == "Bons matchs"
    assert examine["recommendation"] == "À examiner"
    # 4e catégorie du front : moins de 50 %
    assert faible["recommendation"] == "Faible correspondance"
    assert [r["categorie"] for r in (fort, bon, examine, faible)] == ["rec", "good", "review", "low"]


def test_ja044_recalcul_offre_est_idempotent(monkeypatch):
    class Q:
        def __init__(self, values): self.values = values
        def filter(self, *args, **kwargs): return self
        def all(self): return self.values
        def first(self): return self.values[0] if self.values else None

    class DB:
        def __init__(self, offre, resultats, cvs):
            self.offre, self.resultats, self.cvs = offre, resultats, cvs
            self.commits = 0
        def query(self, model):
            if model.__name__ == "Offre": return Q([self.offre])
            if model.__name__ == "Resultat": return Q(self.resultats)
            if model.__name__ == "CV": return Q(self.cvs)
            raise AssertionError(model)
        def commit(self): self.commits += 1
        def close(self): pass

    offre = types.SimpleNamespace(id_offre="offre-1", criteres=[critere("Python", NiveauCritere.OBLIGATOIRE)])
    candidat = cv()
    resultat = types.SimpleNamespace(id_offre="offre-1", id_cv="cv-1", score_sim=0)
    candidat.id_cv = "cv-1"
    db = DB(offre, [resultat], [candidat])

    recalculer_resultats_offre(offre.id_offre, db=db)
    first_score = resultat.score_sim
    recalculer_resultats_offre(offre.id_offre, db=db)

    assert first_score == 100.0
    assert resultat.score_sim == first_score
    assert db.commits == 2


def test_ja044_recalcul_cv_met_a_jour_tous_les_resultats(monkeypatch):
    class Q:
        def __init__(self, values): self.values = values
        def filter(self, *args, **kwargs): return self
        def all(self): return self.values
        def first(self): return self.values[0] if self.values else None

    class DB:
        def __init__(self, cv_obj, resultats, offres): self.cv_obj=cv_obj; self.resultats=resultats; self.offres=offres
        def query(self, model):
            if model.__name__ == "CV": return Q([self.cv_obj])
            if model.__name__ == "Resultat": return Q(self.resultats)
            if model.__name__ == "Offre": return Q(self.offres)
            raise AssertionError(model)
        def commit(self): pass
        def close(self): pass

    candidat = cv()
    candidat.id_cv = "cv-1"
    offre = types.SimpleNamespace(id_offre="offre-1", criteres=[critere("Python", NiveauCritere.OBLIGATOIRE)])
    resultat = types.SimpleNamespace(id_cv="cv-1", id_offre="offre-1", score_sim=0)
    db = DB(candidat, [resultat], [offre])

    recalculer_resultats_cv("cv-1", db=db)
    assert resultat.score_sim == 100.0
