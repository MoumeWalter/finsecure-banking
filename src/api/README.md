# API FastAPI - FinSecure Banking

Module FastAPI exposant les datamarts MongoDB via REST.

## Démarrage

### Via Docker Compose (recommandé)

```powershell
docker compose up -d finsecure_api
```

L'image est construite automatiquement à partir de `Dockerfile.api`.

### En local (dev)

```powershell
# Installer les dépendances
pip install -r requirements-api.txt

# Lancer le serveur avec reload
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

| Méthode | URL | Description |
|---|---|---|
| GET | `/` | Page d'accueil HTML |
| GET | `/docs` | **Swagger UI interactive** |
| GET | `/redoc` | Documentation ReDoc |
| GET | `/health` | Sante API + MongoDB |
| GET | `/api/v1/transactions/{id}` | Détail d'une transaction enrichie |
| GET | `/api/v1/transactions` | Liste paginée (filtres : client, carte, mcc, fraude, dates) |
| GET | `/api/v1/clients/{id}/transactions` | Transactions d'un client |
| GET | `/api/v1/clients/{id}/summary` | Synthèse d'un client (aggregation) |
| GET | `/api/v1/datamarts/mcc` | Top catégories marchands |
| GET | `/api/v1/datamarts/cards` | Top cartes (triable) |
| GET | `/api/v1/datamarts/fraud-stats` | Statistiques de fraude (`$facet`) |

## Tester rapidement

### Avec curl

```bash
# Health
curl http://localhost:8000/health

# Top 5 catégories marchands
curl "http://localhost:8000/api/v1/datamarts/mcc?limit=5"

# Stats fraude
curl http://localhost:8000/api/v1/datamarts/fraud-stats

# Transactions d'un client (utilisez un id reel comme 1066)
curl "http://localhost:8000/api/v1/clients/1066/transactions?page_size=5"
```

### Avec Swagger UI

Ouvrir http://localhost:8000/docs dans un navigateur. Cliquer sur n'importe quel endpoint, "Try it out", remplir les paramètres, "Execute". La réponse JSON s'affiche.

## Architecture du code

```
src/api/
├── main.py              # App FastAPI, lifespan, middlewares, routers
├── config.py            # Settings via Pydantic Settings
├── database.py          # Connexion MongoDB (motor async)
├── models.py            # Schemas Pydantic (request/response)
└── routers/
    ├── health.py
    ├── transactions.py
    ├── clients.py
    └── datamarts.py
```

## Configuration

Variables d'environnement (avec valeurs par défaut) :

| Variable | Défaut | Description |
|---|---|---|
| `MONGO_HOST` | `mongo_db` | Hostname MongoDB (nom du service Docker) |
| `MONGO_PORT` | `27017` | Port MongoDB |
| `MONGO_USER` | `admin` | Utilisateur MongoDB |
| `MONGO_PASSWORD` | `ChangeMeMongo2026` | Mot de passe |
| `MONGO_DATABASE` | `finsecure` | Base de données |
| `MONGO_COLLECTION` | `transactions_enriched` | Collection principale |
| `DEBUG` | `false` | Mode debug FastAPI |
| `DEFAULT_PAGE_SIZE` | `20` | Taille de page par défaut |
| `MAX_PAGE_SIZE` | `200` | Taille de page maximum |

## Évolutions Sprint 2

- Authentification JWT (Phase 11.2)
- Endpoints `POST /predict` pour le scoring ML (Phase 10)
- Rate limiting + observabilité Prometheus (Phase 12)
- Tests pytest exhaustifs avec couverture > 70% (Phase 8)
