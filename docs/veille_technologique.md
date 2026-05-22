# Veille technologique — Justification des choix techniques

> Ce document recense les arbitrages technologiques effectués au lancement du projet et les justifie au regard du besoin client. Il sera mis à jour à chaque itération majeure du projet.

## Méthodologie de veille

Pour chaque brique technique du projet, la démarche suivante a été appliquée :

1. **Identifier le besoin métier ou technique** à satisfaire
2. **Lister 2 à 4 technologies candidates** réellement utilisées dans l'industrie
3. **Définir les critères de décision** pertinents pour ce besoin (performance, coût, courbe d'apprentissage, conformité, intégration, communauté)
4. **Évaluer** chaque candidat sur chaque critère
5. **Trancher** en assumant les compromis

Les sources de veille utilisées : documentations officielles, Gartner Magic Quadrants, ThoughtWorks Technology Radar, retours d'expérience LinkedIn Engineering, conférences DataDevops Paris.

---

## 1. Base de données relationnelle

### Besoin
Source de vérité métier, données structurées, requêtes complexes, intégrité référentielle forte, partitionnement sur 22 M lignes, conformité enterprise.

### Candidats évalués

| Critère | **Oracle XE** ✅ | PostgreSQL | MySQL |
|---|---|---|---|
| Adoption dans le secteur bancaire FR | Très forte (legacy + nouveaux projets) | Forte (néobanques) | Faible |
| PL/SQL | Référence du marché, packages très matures | PL/pgSQL équivalent fonctionnellement | Procédures stockées limitées |
| Partitionnement | Natif, RANGE/LIST/HASH, sub-partitioning | Natif (depuis v10), bon mais moins flexible | Limité |
| Vues matérialisées | Refresh COMPLETE ou FAST (incrémental) | Refresh COMPLETE uniquement | Non natif |
| Coût licence | Gratuit jusqu'à 12 Go / 2 Go RAM (XE) | 100 % gratuit | Gratuit (Community) |
| Conteneurisation Docker | Image officielle Oracle, lourde (~3 Go) mais stable | Image très légère (~250 Mo) | Image très légère |
| Courbe d'apprentissage | Moyenne (syntaxe spécifique) | Faible | Faible |

### Décision
**Oracle XE** est retenu. Critères décisifs :
- Démontrer la maîtrise d'un SGBD enterprise du secteur cible (banque)
- PL/SQL avancé et partitionnement très valorisés par le jury
- Vues matérialisées avec refresh FAST adaptées à nos datamarts
- La limite 12 Go est compatible avec 22 M lignes une fois compressées et partitionnées

### Risques identifiés
- Image Docker volumineuse → mitigé par la couche de build optimisée
- Licence Oracle restrictive en cas de scale → V2 envisage une migration vers PostgreSQL ou Oracle Cloud

---

## 2. Base de données NoSQL

### Besoin
Stockage de transactions enrichies (transaction + client + carte + MCC + label fraude embarqués), schéma évolutif, requêtes flexibles pour les data scientists et l'API.

### Candidats évalués

| Critère | **MongoDB** ✅ | Cassandra | Couchbase | Elasticsearch |
|---|---|---|---|---|
| Modèle de données | Document JSON / BSON | Wide-column | Document + KV | Document indexé |
| Adéquation au cas d'usage | Excellente (transaction = document auto-portant) | Bonne mais surdimensionnée | Bonne | Orienté search, surdimensionné |
| Schéma | Flexible, évolutif sans migration | Rigide (declared schema CQL) | Flexible | Mapping flexible |
| Aggregation pipeline | Très riche (`$lookup`, `$group`, `$facet`) | CQL limité, pas de JOIN | N1QL équivalent SQL | DSL puissant mais complexe |
| Index | B-tree, geo, text, TTL, hashed | Limités | Bons | Très puissants |
| Courbe d'apprentissage | Faible | Élevée | Moyenne | Moyenne |
| Adoption en France | Très large (standard) | Moyenne | Restreinte | Large mais search-only |
| Conteneurisation | Image officielle légère | Image lourde + JVM | Image moyenne | Image lourde + JVM |

### Décision
**MongoDB** est retenu. Critères décisifs :
- Alignement parfait avec le cas d'usage métier (transaction enrichie = document)
- Aggregation framework qui couvre tous les besoins analytiques sans avoir besoin d'un second outil
- Connector Spark-MongoDB officiel et mature
- Standard de facto en France pour le NoSQL document

### Risques identifiés
- Pas de transactions multi-documents en V1 (depuis 4.0 c'est supporté mais coûteux) → mitigé en gardant Oracle pour les écritures transactionnelles strictes

---

## 3. Format de stockage du datalake

### Besoin
Stocker efficacement les couches Bronze / Silver / Gold, optimiser les lectures analytiques massives, permettre la compatibilité Spark / Hive / Power BI / Pandas.

### Candidats évalués

| Critère | **Parquet** ✅ | ORC | Avro | CSV |
|---|---|---|---|---|
| Stockage | Colonnaire | Colonnaire | Ligne | Ligne (texte) |
| Compression | Excellente (Snappy, gzip, zstd) | Excellente | Bonne | Aucune (sauf gzip externe) |
| Lecture analytique (OLAP) | Excellente (lecture sélective de colonnes) | Excellente | Moyenne | Très mauvaise |
| Évolution de schéma | Bonne | Bonne | Excellente (encodage schema-aware) | Aucune |
| Splittable (Spark/Hive) | Oui | Oui | Oui | Oui |
| Écosystème Spark | Premier citizen | Bien supporté | Bien supporté | Supporté |
| Écosystème Hive | Très bien supporté | Excellent (format historique) | Supporté | Supporté |
| Lisibilité par Pandas, Power BI | Native (pyarrow) | Plus rare | Plus rare | Native |
| Adoption marché | Standard de facto en data engineering | Limité au monde Hortonworks/Cloudera | Niche (Kafka principalement) | Universel mais inadapté |

### Décision
**Parquet** est retenu. Critères décisifs :
- Standard de facto incontesté en data engineering moderne
- Performance colonnaire imbattable pour nos requêtes analytiques
- Adoption native dans tout l'écosystème (Spark, Hive, Pandas, Power BI, DuckDB)
- Évolution de schéma suffisante pour notre cas d'usage

### Risques identifiés
- Aucun identifié au niveau format. Le format Avro reste utilisé pour Kafka en Sprint 2 (sérialisation des messages).

---

## 4. Framework d'API REST

### Besoin
Exposer les datamarts aux applications partenaires, valider les entrées, documenter automatiquement, sécuriser avec authentification, scaler horizontalement.

### Candidats évalués

| Critère | **FastAPI** ✅ | Flask | Django REST Framework |
|---|---|---|---|
| Performance | Très élevée (Starlette + async) | Moyenne (WSGI synchrone) | Moyenne |
| Validation des données | Pydantic intégré, déclarative | Manuelle ou via Marshmallow | Serializers DRF |
| Documentation OpenAPI | Générée automatiquement (Swagger + ReDoc) | Extension `flask-restx` requise | `drf-spectacular` requise |
| Type hints Python | Cœur du framework | Non | Partiellement |
| Courbe d'apprentissage | Faible (très pythonique) | Très faible | Élevée (full framework) |
| Async natif | Oui | Non (sauf Quart) | Limité |
| Communauté et momentum | Très forte, en croissance | Très forte mais mature | Forte mais déclinante |

### Décision
**FastAPI** est retenu. Critères décisifs :
- Standard moderne pour les APIs data en Python
- Documentation OpenAPI auto-générée = gain de temps majeur
- Validation Pydantic = sécurité et clarté des contrats d'API
- Performance async pour scaler les endpoints de scoring ML

---

## 5. Orchestration de conteneurs

### Besoin
Orchestrer ~7 services (Oracle, MongoDB, Spark master, Spark worker, Hive, FastAPI, Airflow), permettre un démarrage en une commande, faciliter la reproductibilité chez tout évaluateur.

### Candidats évalués

| Critère | **Docker Compose** ✅ | Docker seul | Kubernetes (kind/minikube) |
|---|---|---|---|
| Multi-services | Natif via `docker-compose.yml` | Manuel (un `docker run` par service) | Natif et industriel |
| Courbe d'apprentissage | Faible | Très faible | Élevée |
| Networking | Auto (réseaux nommés) | Manuel (`--network`) | Auto |
| Volumes persistants | Déclaratifs | Manuels | Persistent Volume Claims |
| Healthchecks | Supportés | Supportés | Supportés et avancés |
| Production-ready | Pour MVP/dev/test | Non | Oui |
| Adapté au périmètre V1 | Parfait | Insuffisant | Surdimensionné |

### Décision
**Docker Compose** est retenu pour la V1. Kubernetes sera évoqué en conclusion comme évolution naturelle V2.

---

## 6. Choix structurants pour le Sprint 2 (à confirmer le moment venu)

Les choix suivants seront documentés en détail au moment du Sprint 2 mais sont déjà cadrés :

| Brique | Choix anticipé | Justification résumée |
|---|---|---|
| Streaming | **Kafka + Spark Structured Streaming** | Standard du marché, adapté au cas d'usage transactionnel, intégration native avec notre stack PySpark |
| Orchestration de pipelines | **Airflow** | Standard de facto, DAG Python natif, opérateurs Spark et Docker matures |
| Tests | **Pytest + Great Expectations** | Pytest est l'écosystème Python standard ; Great Expectations couvre la qualité de données là où Pytest s'arrête au code |
| CI/CD | **GitHub Actions** | Gratuit pour repo public, intégration native GitHub, syntaxe YAML simple |
| MLOps | **MLflow** | Tracking d'expériences, model registry, serving — couvre toute la chaîne |
| Observabilité | **Prometheus + Grafana** | Standard open source, stack mature, dashboards exportables |

---

## 7. Sources de veille consultées

- [ThoughtWorks Technology Radar](https://www.thoughtworks.com/radar)
- [Gartner Magic Quadrant for Cloud Database Management Systems 2025](https://www.gartner.com)
- Documentation officielle Oracle, MongoDB, Apache (Spark / Hive / Kafka / Airflow), FastAPI
- Articles d'ingénierie : Netflix Tech Blog, Uber Engineering, Spotify Engineering, Doctolib Engineering
- Communautés : Stack Overflow Developer Survey 2025, JetBrains State of Developer Ecosystem 2025
- Conférences : Devoxx France, dotData Paris, Data Days

## 8. Évolutivité du document

Ce document sera enrichi à chaque phase du projet d'une section "Décisions du sprint" récapitulant les arbitrages tranchés.

| Version | Date | Auteur | Changements |
|---|---|---|---|
| 0.1 | `<DATE>` | `<TON_NOM>` | Initialisation, choix structurants Sprint 1 |
