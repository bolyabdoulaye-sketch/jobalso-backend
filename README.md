# Jobalso Backend

API de Jobalso : comptes candidats et recruteurs, organisations, offres avec critères
hiérarchisés, dépôt et analyse de CV, shortlist expliquée, pipeline des candidatures.

## Stack technique

- FastAPI + SQLAlchemy 2 + Alembic (Python 3.14)
- PostgreSQL 16 avec l'extension pgvector
- RustFS (stockage compatible S3, client MinIO) pour les fichiers de CV
- Mailpit (serveur SMTP de développement : capture les emails sans les envoyer)
- pgAdmin (administration de la base)

## Démarrer en local (Docker)

Prérequis : Docker Desktop lancé, Git.

```bash
git clone <url-du-repo>
cd jobalso-backend
cp .env.example .env
```

Compléter `.env` (mots de passe, clés de stockage, et `SECRET_KEY`, obligatoire) :

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Puis :

```bash
docker compose up --build
```

Le service `migrate` applique les migrations Alembic, puis l'API démarre.

| Service | Adresse |
|---|---|
| API et documentation interactive | http://localhost:8000/docs |
| Santé (API + base) | http://localhost:8000/health |
| Emails envoyés (Mailpit) | http://localhost:8025 |
| Console du stockage (RustFS) | http://localhost:9001 |
| pgAdmin | http://localhost:5050 |

En développement, l'API recharge le code à chaud (`app/` est monté dans le conteneur).
L'image seule (production) tourne sans rechargement, avec un utilisateur non root.

## Tests

Les tests d'intégration tournent sur une vraie base PostgreSQL et rejouent toutes les
migrations depuis zéro. Le stockage et les emails y sont simulés.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker run -d --name jobalso_test_db -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=jobalso_test -p 55432:5432 pgvector/pgvector:pg16
TEST_DATABASE_URL=postgresql://test:test@localhost:55432/jobalso_test pytest
ruff check app alembic/env.py
pip-audit -r requirements.txt
```

Sans `TEST_DATABASE_URL`, seuls les tests unitaires tournent.

La CI GitHub Actions (`.github/workflows/ci.yml`) exécute à chaque push et pull request :
lint, audit des dépendances, tests unitaires et d'intégration, `alembic check`
(modèles et migrations cohérents), et construction de l'image Docker.

## Contrat pour le front

Toutes les routes sont préfixées par `/api/v1`. La documentation complète est sur `/docs`.

### Authentification

- `POST /auth/login` (formulaire OAuth2 : `username` = email, `password`) renvoie
  `access_token` (15 min), `refresh_token` (14 jours), `expires_in`, `type_utilisateur`, `persona`.
- `POST /auth/refresh {refresh_token}` renvoie une nouvelle paire. L'ancien jeton devient
  invalide ; le réutiliser ferme toutes les sessions du compte (vol probable).
- `POST /auth/logout {refresh_token}`.
- `GET /auth/me` : profil, `status` (`EN_ATTENTE` tant que l'email n'est pas confirmé),
  `id_organisation` et `role_organisation` pour un recruteur.

### Pages que le front doit prévoir

Les emails contiennent des liens vers le front (`FRONTEND_URL`) :

| Page du front | Appel à faire avec `?token=` |
|---|---|
| `/verifier-email` | `POST /auth/verify-email {token}` |
| `/reinitialiser-mot-de-passe` | `POST /auth/reset-password {token, nouveau_mot_de_passe}` (sert aussi à activer les comptes créés par une candidature publique) |
| `/invitation` | connecté en recruteur : `POST /organisation/invitations/accept {token}` |

### Règles métier

- À l'inscription, un recruteur reçoit sa propre organisation (`nom_organisation`
  facultatif) dont il est ADMIN.
- Tous les membres d'une organisation gèrent ses offres, la shortlist et le pipeline.
  Seuls l'auteur d'une offre et les ADMIN peuvent la supprimer. Seuls les ADMIN
  invitent, retirent des membres et renomment l'organisation.
- Un recruteur appartient à une seule organisation. Accepter une invitation remplace
  l'organisation créée à l'inscription si elle est encore vide ; sinon, refus (409).
  `POST /organisation/quitter` permet de partir, sauf si l'organisation resterait
  sans membre ou sans ADMIN. Un recruteur sans organisation en crée une avec
  `POST /organisation`.
- `status: false` à la création d'une offre = brouillon, invisible par le lien public.
- La candidature publique (`/public/offres/{token}/postuler`) est réservée aux personnes
  sans compte ; un candidat inscrit postule avec `POST /candidatures/offres/{token}`.
- Supprimer une offre supprime ses candidatures. Supprimer son CV supprime le fichier
  stocké et les candidatures liées (droit à l'effacement, Loi 25).

### Shortlist et tableau de bord

`GET /offres/{id}/resultats` renvoie, triées par score, les candidatures avec
`categorie` (`rec`, `good`, `review`, `low`, comme le front), `recommendation`,
`criteres_valides`, `ecarts` et un aperçu `candidat` (nom, localisation, compétences,
langues, code CV). `GET /offres/tableau-de-bord` donne les compteurs par offre.

| Catégorie | Score |
|---|---|
| `rec` Fortement recommandés | 88 % et plus |
| `good` Bons matchs | 72 à 87,9 % |
| `review` À examiner | 50 à 71,9 % |
| `low` Faible correspondance | moins de 50 % |

Un critère obligatoire manquant plafonne le score à 71,9 %.

### Limites de requêtes

Connexion, inscription, mot de passe oublié, candidature publique, dépôt de CV et
matching par code CV sont limités (réponse `429` avec l'en-tête `Retry-After`).
Les compteurs sont en mémoire du processus : avec plusieurs instances, il faudra un
stockage partagé (Redis).
