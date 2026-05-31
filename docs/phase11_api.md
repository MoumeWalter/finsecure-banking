# Phase 11 — API REST FastAPI

> Cette phase expose les datamarts MongoDB via une API REST moderne.

## Sommaire

1. [Objectif et valeur métier](#1-objectif-et-valeur-métier)
2. [Choix technologiques](#2-choix-technologiques)
3. [Architecture](#3-architecture)
4. [Endpoints](#4-endpoints)
5. [Démonstration au jury](#5-démonstration-au-jury)
6. [Décisions et trade-offs](#6-décisions-et-trade-offs)

---

## 1. Objectif et valeur métier

### Contexte

Les datamarts MongoDB (vues `v_card_aggregates`, `v_mcc_aggregates`, `v_daily_aggregates`) contiennent des informations précieuses pour :

- Les **analystes risque** qui veulent identifier les cartes à risque
- Les **équipes marketing** qui ciblent par catégorie marchand
- Les **systèmes externes** (Power BI, futurs modèles ML)

Sans API, ces données ne sont accessibles qu'à des utilisateurs techniques connaissant `mongosh`. L'API REST démocratise l'accès.

### Valeur ajoutée

| Avant l'API | Après l'API |
|---|---|
| `mongosh` requis | n'importe quel client HTTP |
| Pas de validation | Validation Pydantic des paramètres |
| Pas de documentation | Swagger UI auto-générée |
| Pas de gouvernance | Endpoints versionnés `/api/v1/...` |
| Pas de réutilisation | Power BI, ML, mobile, web peuvent consommer |

---

## 2. Choix technologiques

### FastAPI plutôt que Flask / Django REST

| Critère | FastAPI ✅ | Flask | Django REST |
|---|---|---|---|
| Performance async native | ✅ Excellente | ❌ WSGI bloquant | ❌ WSGI bloquant |
| Validation auto | ✅ Pydantic | ❌ Marshmallow externe | 🟡 Serializers verbeux |
| Documentation auto | ✅ Swagger + Redoc | ❌ Aucune | 🟡 Plug-in |
| Type hints natifs | ✅ Idiomatique | ❌ | 🟡 |
| Adoption récente | ✅ Standard moderne | 🟡 Legacy | 🟡 Lourd |

### Motor (MongoDB async)

`motor` est le driver MongoDB officiel async, basé sur asyncio. Pourquoi async ?

- Une requête MongoDB peut prendre 10-100 ms (I/O)
- En sync, le serveur ne peut traiter qu'une requête à la fois pendant ce temps
- En async, le serveur traite d'autres requêtes pendant l'attente I/O

**Bénéfice concret** : à charge égale, FastAPI + Motor peut servir 5-10x plus de requêtes simultanées qu'un Flask + pymongo synchrone.

### Pydantic v2 pour les schemas

- Validation automatique des paramètres entrants (query, path, body)
- Sérialisation automatique des réponses en JSON
- Génération automatique du schéma OpenAPI (= Swagger UI)
- Type hints Python natifs : pas de DSL particulier à apprendre

---

## 3. Architecture

```
┌──────────────────────────────────────────────┐
│              CLIENT HTTP                      │
│  Postman / curl / Power BI / navigateur      │
└──────────────────┬───────────────────────────┘
                   │ HTTP/JSON
                   ▼
┌──────────────────────────────────────────────┐
│           finsecure_api (conteneur)          │
│                                              │
│  FastAPI                                     │
│   ├── /docs (Swagger)                        │
│   ├── /health                                │
│   └── /api/v1/                               │
│       ├── transactions    (router)           │
│       ├── clients         (router)           │
│       └── datamarts       (router)           │
│                                              │
│  Motor (async)                               │
└──────────────────┬───────────────────────────┘
                   │ MongoDB Wire Protocol
                   ▼
┌──────────────────────────────────────────────┐
│           mongo_db (conteneur)               │
│  Collections :                               │
│   - transactions_enriched (100k docs)        │
│  Vues :                                      │
│   - v_card_aggregates                        │
│   - v_mcc_aggregates                         │
│   - v_daily_aggregates                       │
└──────────────────────────────────────────────┘
```

### Structure du code

```
src/api/
├── main.py              # App FastAPI, lifespan, middlewares
├── config.py            # Pydantic Settings (env-based)
├── database.py          # Connexion MongoDB
├── models.py            # 14 schemas Pydantic
└── routers/
    ├── health.py        # GET /health
    ├── transactions.py  # 2 endpoints
    ├── clients.py       # 2 endpoints
    └── datamarts.py     # 3 endpoints
```

### Pattern Lifespan

L'app utilise le pattern `lifespan` de FastAPI (recommandé depuis 0.95) pour :
- Ouvrir la connexion MongoDB **au démarrage** (pas à la première requête)
- Fermer proprement la connexion **à l'arrêt**

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_mongo()
    yield
    await close_mongo()
```

---

## 4. Endpoints

### Monitoring

| Méthode | URL | Description |
|---|---|---|
| GET | `/health` | État API + MongoDB + nb documents |

### Transactions

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/v1/transactions/{id}` | Détail enrichi |
| GET | `/api/v1/transactions` | Liste paginée + 7 filtres |

### Clients

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/v1/clients/{id}/transactions` | Liste paginée |
| GET | `/api/v1/clients/{id}/summary` | Synthèse aggrégée |

### Datamarts

| Méthode | URL | Description |
|---|---|---|
| GET | `/api/v1/datamarts/mcc` | Top catégories marchands |
| GET | `/api/v1/datamarts/cards` | Top cartes (triable) |
| GET | `/api/v1/datamarts/fraud-stats` | Statistiques `$facet` |

### Exemples d'appels

```bash
# Santé
curl http://localhost:8000/health

# Détail d'une transaction
curl http://localhost:8000/api/v1/transactions/7475327

# Top 5 catégories marchands
curl "http://localhost:8000/api/v1/datamarts/mcc?limit=5"

# Cartes à risque (taux fraude desc, min 100 tx)
curl "http://localhost:8000/api/v1/datamarts/cards?sort_by=taux_fraude_pct&sort_desc=true&min_transactions=100"

# Stats fraude
curl http://localhost:8000/api/v1/datamarts/fraud-stats

# Synthèse client (client 1066 a 136 tx)
curl http://localhost:8000/api/v1/clients/1066/summary

# Transactions d'un client paginées
curl "http://localhost:8000/api/v1/clients/1066/transactions?page=1&page_size=10"

# Liste filtrée (fraudes uniquement)
curl "http://localhost:8000/api/v1/transactions?is_fraud=true&page_size=10"
```

---

## 5. Démonstration au jury

### Storytelling

> "J'ai exposé les datamarts MongoDB via une API REST FastAPI. Trois bénéfices : la **démocratisation** (n'importe quel client HTTP peut interroger), la **documentation auto-générée** sur `/docs` qui sert de contrat d'interface, et la **performance** grâce à l'async natif de FastAPI + Motor."

### Démo en 3 minutes

**1. Page d'accueil (15 s)**

Ouvrir http://localhost:8000 → expliquer ce qu'on voit (lien Swagger, endpoints listés).

**2. Swagger UI (1 min)**

Ouvrir http://localhost:8000/docs → faire défiler la liste des endpoints.

Choisir `GET /api/v1/datamarts/fraud-stats` → "Try it out" → "Execute" → montrer la réponse JSON.

Surligner : **"91,6 % des fraudes sont des transactions en ligne, 72 % concernent des femmes"**. Ce sont des insights métier extraits en une requête.

**3. Endpoint cartes à risque (1 min)**

Dans Swagger, `GET /api/v1/datamarts/cards` → paramètres :
- `sort_by` = `taux_fraude_pct`
- `sort_desc` = `true`
- `min_transactions` = `100`

Execute → montrer la carte 2019 avec 8,57 % de fraude.

> "Voilà comment le département Risque accède aux cartes à surveiller en une requête HTTP. Avant l'API, il fallait une connaissance MongoDB. Maintenant, n'importe quelle application peut consommer ces données."

**4. /health (30 s)**

Ouvrir http://localhost:8000/health → montrer `status: ok`, `estimated_documents: 100000`.

> "L'API expose son état pour le monitoring. En production, Prometheus scrapperait cet endpoint."

---

## 6. Décisions et trade-offs

### Pas d'authentification (pour l'instant)

**Décision** : pas de JWT pour cette première version.

**Justification** :
- Phase de développement, démo locale, pas exposé à internet
- L'auth complète sera ajoutée en V2 quand on aura des cas d'usage réels (mobile, partenaires)
- Permet de garder le code lisible pour le jury

**À ajouter en V2** :
- `python-jose` pour les tokens JWT
- Dépendance `Depends(get_current_user)` sur les routes sensibles
- Endpoint `/auth/login` avec validation password + génération token

### MongoDB uniquement (pas d'Oracle)

**Décision** : l'API n'interroge que MongoDB.

**Justification** :
- MongoDB sert l'analytique → naturel pour une API exposant des datamarts
- Documents auto-portants → 1 requête = 1 réponse complète (pas de jointure)
- Performance > 10x supérieure à Oracle pour ces requêtes
- Oracle reste la source de vérité, accessible directement aux apps internes

**Cohérence avec l'architecture polyglot** :
- Oracle = OLTP + audit + transactions ACID
- MongoDB = OLAP + API + ML
- Les deux ont leur rôle, pas de doublon

### Stratégie de pagination

**Décision** : pagination "skip + limit" classique.

**Limites connues** :
- Le `skip` devient lent pour les grandes pages (page 1000 + page_size 100 = skip 99900)
- Pour > 10 000 documents, préférer la pagination par curseur (`_id` ou `date_transaction`)

**Acceptable ici** car notre dataset MongoDB fait 100k documents et les requêtes typiques ne dépassent pas page 100.

### Pas de cache HTTP

**Décision** : pas de cache (ni Cache-Control, ni Redis).

**Justification** : MongoDB est déjà très rapide (< 50 ms par requête typique). Le cache ajouterait de la complexité sans valeur immédiate.

**À ajouter en V2** : Redis pour les endpoints les plus chauds (`/datamarts/mcc`, `/datamarts/fraud-stats`) avec TTL de 5 min.

---

## Conformité au Bloc 1 (compétence API)

Cette phase couvre la compétence du Bloc 1 :

> *"Concevoir et développer une API pour exposer les données du système d'information à des consommateurs externes"*

| Démonstration | Statut |
|---|---|
| API REST conforme à OpenAPI | ✅ FastAPI + spec OpenAPI auto |
| Versionnement | ✅ Préfixe `/api/v1/` |
| Documentation auto | ✅ Swagger UI + ReDoc |
| Validation des entrées | ✅ Pydantic |
| Sérialisation cohérente | ✅ Schemas Pydantic |
| Conteneurisation | ✅ Dockerfile + compose |
| Healthcheck | ✅ `/health` + Docker HEALTHCHECK |
