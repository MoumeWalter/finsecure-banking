# FinSecure Banking — Plateforme data de détection de fraude

> Projet certifiant RNCP36739 — Expert en Ingénierie de Données
> Master 2 Data Engineering & IA — EFREI Paris Panthéon-Assas
> Auteur : `<TON_NOM>` — Soutenance : `<MOIS_ANNÉE>`

## Contexte

FinSecure Banking est une banque de détail française fictive qui souhaite moderniser sa plateforme de détection de fraude et de reporting réglementaire. Ce projet implémente une **plateforme data de bout en bout** intégrant :

- Une **base relationnelle Oracle** modélisée selon Merise pour la source de vérité métier
- Une **base NoSQL MongoDB** pour exposer les transactions enrichies aux usages analytiques et ML
- Un **datalake Hive + Parquet** structuré en architecture médaillon (Bronze / Silver / Gold)
- Une **API REST FastAPI** sécurisée pour exposer les datamarts
- Un **pipeline ML Spark MLlib** pour détecter les transactions frauduleuses
- Une **orchestration complète Docker Compose**

## Blocs de compétence visés

Ce projet couvre intégralement les **blocs 1 et 2** du référentiel RNCP36739 :

- **Bloc 1** — Concevoir et développer une architecture de stockage de données : BDR Oracle modélisée, NoSQL MongoDB, Datalake, API REST
- **Bloc 2** — Concevoir, développer et déployer une solution de traitement de données massives : ingestion multi-sources, transformations PySpark, ordonnancement Airflow, streaming Kafka, conteneurisation Docker, CI/CD GitHub Actions

## Architecture cible

Voir [`docs/architecture_cible.md`](docs/architecture_cible.md).

## Structure du projet

```
finsecure-banking/
├── README.md
├── .gitignore
├── .env.example
├── docs/                      # Documentation projet
│   ├── cadrage_client.md
│   ├── architecture_cible.md
│   ├── architecture_cible.svg
│   └── veille_technologique.md
├── data/                      # Datasets (non versionnés, voir data/README.md)
├── sql/                       # Scripts DDL/DML Oracle, vues, procédures PL/SQL
├── src/                       # Code Python applicatif (modules réutilisables)
├── notebooks/                 # Notebooks d'exploration et de pipeline
├── docker/                    # Dockerfiles et docker-compose.yml
├── dags/                      # DAGs Airflow d'ordonnancement
└── tests/                     # Tests unitaires et d'intégration
```

## Prérequis

- Docker Desktop ≥ 24.0
- Git ≥ 2.40
- Python 3.11 (pour scripts locaux hors conteneurs)
- 16 Go RAM minimum recommandé

## Démarrage rapide

```bash
# Cloner le projet
git clone https://github.com/<TON_USER>/finsecure-banking.git
cd finsecure-banking

# Copier le fichier d'environnement
cp .env.example .env
# (éditer .env avec vos identifiants Oracle / MongoDB)

# Lancer l'infrastructure complète
docker compose -f docker/docker-compose.yml up -d

# Vérifier que tous les services sont up
docker compose -f docker/docker-compose.yml ps
```

## Roadmap

Le projet est structuré en deux sprints. Voir [`docs/roadmap.md`](docs/roadmap.md) pour le détail.

| Sprint | Phases | Objectif |
|---|---|---|
| **Sprint 1** (Bloc 1) | Cadrage → Modélisation → BDR Oracle → MongoDB → Datalake → API | Solidifier la couche stockage |
| **Sprint 2** (Bloc 2) | Conteneurisation → Streaming → Orchestration → Tests → CI/CD → ML → Observabilité | Industrialiser et fiabiliser |

## Licence

MIT — Voir [`LICENSE`](LICENSE).
