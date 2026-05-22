# Roadmap projet

## Vue d'ensemble en 2 sprints

| Sprint | Bloc RNCP visé | Phases | Durée estimée |
|---|---|---|---|
| **Sprint 1** | Bloc 1 — Stockage de données | 0 → 1 → 2 → 3 → 4 → 11 | ~6 semaines |
| **Sprint 2** | Bloc 2 — Traitement de données massives + transverses | 5 → 6 → 7 → 8 → 9 → 10 → 12 → 13 | ~8 semaines |

## Sprint 1 — Solidifier la couche stockage

### Phase 0 — Cadrage et veille ✅ (livré)

- [x] Document de cadrage client
- [x] Schéma d'architecture cible
- [x] Document de veille technologique
- [x] Repository Git initialisé

### Phase 1 — Modélisation Merise

- [ ] MCD complet (entités, relations, cardinalités)
- [ ] MLD en 3NF (avec dénormalisations justifiées si nécessaire)
- [ ] MPD Oracle (types `NUMBER`, `VARCHAR2`, `DATE`, `TIMESTAMP`…)
- [ ] Dictionnaire de données

### Phase 2 — Base de données relationnelle Oracle

- [ ] DDL : `CREATE TABLE` avec PK, FK, CHECK, UNIQUE, NOT NULL
- [ ] Séquences pour les IDs
- [ ] Index : B-tree sur FK, bitmap sur `fraudulent`, index composite
- [ ] Partitionnement RANGE par mois sur les transactions
- [ ] Vues : `v_transactions_enrichies`, `mv_card_aggregates` (matérialisée)
- [ ] PL/SQL : procédures, fonctions, package `pkg_datamart`
- [ ] Triggers d'audit et d'historisation
- [ ] Sécurité : 5 rôles, GRANT/REVOKE, schémas séparés
- [ ] EXPLAIN PLAN sur 3 requêtes critiques
- [ ] Script de migration SQLite → Oracle

### Phase 3 — Base NoSQL MongoDB

- [ ] Document de justification du choix MongoDB
- [ ] Modélisation des documents (transaction auto-portante)
- [ ] Script d'ingestion depuis Silver via le connector PySpark-MongoDB
- [ ] Index MongoDB (client_id, situation_date, TTL d'archivage)
- [ ] Aggregation pipeline équivalent aux datamarts Gold

### Phase 4 — Datalake formalisé

- [ ] Reprise du `feeder.ipynb` en module Python `src/bronze.py` testable
- [ ] Reprise du `preprocessing.ipynb` en module `src/silver.py`
- [ ] Reprise du `datamart.ipynb` en module `src/gold.py`
- [ ] Validation de schéma à l'entrée Bronze
- [ ] Métriques de pipeline documentées (taille, durée, taux de rejet)

### Phase 11 — API REST enrichie

- [ ] Endpoint `POST /predict` qui charge le modèle ML
- [ ] CRUD complet sur les datamarts (GET, POST, PUT, DELETE)
- [ ] Authentification OAuth2 + JWT
- [ ] Validation Pydantic sur tous les inputs
- [ ] Pagination des endpoints liste
- [ ] Rate limiting avec slowapi
- [ ] Documentation Swagger enrichie
- [ ] Endpoint `/health`

## Sprint 2 — Industrialiser et fiabiliser

### Phase 5 — Conteneurisation
- [ ] Dockerfiles dédiés par service
- [ ] `docker-compose.yml` orchestrant tout
- [ ] Volumes persistants, healthchecks, dépendances
- [ ] Makefile (`make up`, `make down`, `make logs`, `make test`)

### Phase 6 — Streaming
- [ ] Kafka + Zookeeper dans le compose
- [ ] Topic `transactions_stream`
- [ ] Producteur Python rejouant l'historique
- [ ] Consumer Spark Structured Streaming avec scoring ML
- [ ] Fenêtres tumbling 5 minutes

### Phase 7 — Ordonnancement
- [ ] Airflow dans le compose
- [ ] DAG batch quotidien complet
- [ ] DAG ML hebdomadaire de réentraînement
- [ ] Retries, SLA, notifications

### Phase 8 — Tests
- [ ] Tests unitaires Pytest
- [ ] Tests d'intégration sur pipeline complet
- [ ] Tests API avec httpx
- [ ] Tests qualité de données avec Great Expectations
- [ ] Couverture ≥ 70 %

### Phase 9 — CI/CD
- [ ] Workflow GitHub Actions (lint, test, build, push)
- [ ] Pre-commit hooks (black, flake8, isort)
- [ ] Versioning sémantique
- [ ] Branch protection sur `main`

### Phase 10 — ML solidifié
- [ ] Gestion du déséquilibre de classes
- [ ] Cross-validation
- [ ] Tuning d'hyperparamètres
- [ ] Métriques complètes (AUC-PR, F1, matrice confusion)
- [ ] MLflow pour tracking
- [ ] Feature engineering avancé

### Phase 12 — Observabilité
- [ ] Logger structuré
- [ ] Prometheus pour métriques
- [ ] Grafana dashboards
- [ ] Alerting

### Phase 13 — Documentation finale
- [ ] README complet
- [ ] `docs/architecture.md` enrichi
- [ ] `docs/data_model.md`
- [ ] `docs/api.md`
- [ ] Rapport technique final
- [ ] Slides de soutenance
