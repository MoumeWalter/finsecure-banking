# Récap pédagogique — Ce qui a été fait dans le projet

> Ce document est un **guide de lecture** pour comprendre rapidement la valeur du projet.
> Idéal pour la préparation à la soutenance ou pour onboarder un nouveau contributeur.

---

## Vue d'ensemble en 30 secondes

J'ai construit la **brique relationnelle complète** d'une plateforme data bancaire :

- **9 tables Oracle** modélisées selon Merise (MCD, MLD, MPD)
- **22,5 millions d'objets** réels migrés depuis 5 sources hétérogènes
- **Chiffrement AES-256** de 6 colonnes sensibles (RGPD/PCI-DSS)
- **8 147 opérations tracées** automatiquement par audit ACPR
- **Partitionnement + 12 index** validés par EXPLAIN PLAN
- **3 datamarts matérialisés** prêts pour Power BI et l'API

Le tout reproductible **en 3 commandes** chez n'importe quel évaluateur (voir [README](../README.md)).

---

## Ce qui rend ce projet solide pour le jury

### 1. Une démarche d'ingénieur, pas un TP

Le projet suit une **méthodologie d'ingénierie data réelle** :

1. **Cadrage métier d'abord** (scénario FinSecure Banking documenté)
2. **Conception théorique** ensuite (MCD → MLD → MPD avec justifications)
3. **Implémentation technique** après (DDL + PL/SQL + sécurité)
4. **Migration de données réelles** pour valider l'implémentation
5. **Inspection a posteriori** des EXPLAIN PLAN pour prouver l'efficacité
6. **Documentation des difficultés rencontrées** et de leurs résolutions

C'est cette **chronologie complète** qui distingue un projet abouti d'un TP isolé.

### 2. Des chiffres concrets à raconter

| Élément | Chiffre |
|---|---|
| Lignes en base | 22 533 698 |
| Temps total de migration | 5 h 40 |
| Volume disque Oracle | 9,7 Go |
| Index créés et validés | 12 |
| Partitions créées automatiquement | 2 (P_INITIAL + SYS_P987) |
| Opérations tracées par triggers | 8 147 |
| Colonnes chiffrées | 6 (sur 2 tables) |
| Vues matérialisées | 3 (4 071 + 1 + 109 lignes) |

Tous **vérifiés par requêtes SQL** que tu peux relancer en direct au jury.

### 3. Des arguments défendables sur chaque choix

Pour chaque décision technique, le projet documente :

- **L'alternative écartée**
- **Le critère décisionnel**
- **Le compromis accepté**

Exemples :
- Oracle XE plutôt que PostgreSQL : "standard du secteur bancaire français"
- Pas de SCD2 sur CLIENT : "dataset sans snapshots multi-périodes, on garde la complexité pour des cas pertinents"
- Table MARCHAND dérivée par DISTINCT : "élimination de redondance massive, démonstration fait/dimension"

Voir [`veille_technologique.md`](veille_technologique.md) pour le détail.

---

## La structure du projet expliquée

```
finsecure-banking/
├── README.md                          ← Guide principal pour reproduire
├── CONTRIBUTING.md                    ← Conventions Git / code
├── LICENSE                            ← MIT
├── .gitignore                         ← Ignore data/raw/, .env, .venv/
├── .env.example                       ← Template (jamais commiter le vrai .env)
├── requirements-migration.txt         ← Dépendances Python
├── run_all_sql.ps1                    ← Script PowerShell d'orchestration SQL
│
├── docs/                              ← TOUTE la documentation
│   ├── rapport_technique.md           ← LE document principal (refonte compte-rendu)
│   ├── recap_pedagogique.md           ← CE document
│   ├── cadrage_client.md              ← Scénario FinSecure
│   ├── architecture_cible.md          ← Architecture en mots
│   ├── architecture_cible.svg         ← Architecture en schéma (pour slides)
│   ├── veille_technologique.md        ← Justification de chaque choix techno
│   ├── phase2_implementation.md       ← Détail de la Phase 2
│   ├── roadmap.md                     ← Plan en 13 phases
│   ├── plan1_partitionnement.txt      ← EXPLAIN PLAN partition pruning
│   ├── plan2_jointures.txt            ← EXPLAIN PLAN jointures
│   ├── plan3_lookup_pk.txt            ← EXPLAIN PLAN lookup PK
│   └── data_model/
│       ├── modele_donnees.md          ← MCD / MLD / MPD complet
│       ├── dictionnaire_donnees.md    ← Description colonne par colonne
│       └── schema_mld_mpd.svg         ← Diagramme ERD pour slides
│
├── sql/                               ← Scripts DDL/DML
│   ├── README.md                      ← Ordre d'exécution
│   ├── 00_init_for_official_xe.sql    ← Tablespaces + utilisateur + rôles
│   ├── 02_sequences.sql               ← 3 séquences
│   ├── 03_tables.sql                  ← 9 tables avec contraintes
│   ├── 04_indexes.sql                 ← 12 index + statistiques
│   ├── 05_views.sql                   ← 3 vues métier
│   ├── 06_materialized_views.sql      ← 3 datamarts
│   ├── 07_packages_plsql.sql          ← Package pkg_datamart
│   ├── 08_triggers.sql                ← 5 triggers
│   ├── 01_grants.sql                  ← Droits aux rôles
│   ├── 09_explain_plans.sql           ← Requêtes de test
│   ├── 99_cleanup.sql                 ← Nettoyage complet (rollback)
│   ├── 99_fix_migration.sql           ← Patch 1 : types VARCHAR2 pour KYC
│   └── 99_fix_migration_v2.sql        ← Patch 2 : relaxation CHECK
│
└── src/migration/                     ← Code Python
    ├── README.md                      ← Procédure de migration
    ├── __init__.py
    ├── encryption.py                  ← AES-256-GCM
    └── load_oracle.py                 ← Pipeline ETL complet
```

---

## Les 6 difficultés résolues (et leur valeur)

Chaque difficulté rencontrée et résolue est **un point fort** à mentionner. Voici les 6 principales :

### 1. Le bootstrap des triggers d'audit
**Problème** : œuf et poule (le trigger référence une table qui doit d'abord se peupler).
**Résolution** : désactivation/réactivation temporaire du trigger pour insérer un compte SYSTEM.
**Ce que ça démontre** : compréhension fine des mécanismes Oracle, pensée "qu'est-ce qui se passe en cas limite".

### 2. Le partitionnement avec PK
**Problème** : `USING INDEX LOCAL` exige que la colonne de partitionnement fasse partie de la PK.
**Résolution** : passage à un index PK GLOBAL.
**Ce que ça démontre** : connaissance des règles Oracle sur le partitionnement, trade-off LOCAL vs GLOBAL.

### 3. Les contraintes trop strictes vs données réelles
**Problème** : 3 contraintes UNIQUE/CHECK qui refusaient les vraies données.
**Résolution** : relaxation argumentée des contraintes après inspection.
**Ce que ça démontre** : démarche itérative, capacité à reconnaître quand la théorie doit s'adapter.

### 4. NaN pandas vs VARCHAR2 Oracle
**Problème** : `oracledb` refuse `float('nan')` pour une colonne texte.
**Résolution** : helpers défensifs `s()`, `i()`, `f()` qui convertissent les NaN systématiquement.
**Ce que ça démontre** : robustesse du code de production, gestion des cas limites au niveau du driver.

### 5. Encodage UTF-8 + BOM + SQL*Plus
**Problème** : PowerShell ajoute un BOM UTF-8 qui fait crier SQL*Plus.
**Résolution** : `-Encoding ascii` systématique pour les scripts SQL.
**Ce que ça démontre** : connaissance des subtilités cross-platform Windows → Linux Docker.

### 6. Performance Oracle XE
**Constat** : 740 inserts/sec sur XE (limité à 2 Go RAM), serait 10x plus sur Enterprise.
**Ce que ça démontre** : capacité à mesurer, à mettre en perspective, à parler du dimensionnement en V2.

---

## Le storytelling pour la soutenance

### Slide 1 : Le contexte
> "FinSecure Banking est une banque française fictive qui perd 3,2 M€ par an à cause d'une détection de fraude trop lente. J'ai conçu et implémenté la couche relationnelle d'une plateforme moderne pour résoudre ce problème."

### Slide 2 : L'architecture
Montrer le schéma SVG, expliquer en 2 minutes les 4 couches (sources → datalake → stockages → consommation).

### Slide 3 : La modélisation
"J'ai suivi la démarche Merise classique. 9 entités, 5 décisions de modélisation justifiées. Voici le MCD." (montrer le schéma ERD)

### Slide 4 : L'implémentation Oracle
"3 tablespaces, 9 tables, 12 index, partitionnement RANGE INTERVAL, package PL/SQL avec 4 procédures et 4 fonctions, 5 triggers d'audit."

### Slide 5 : La sécurité
"Chiffrement AES-256-GCM sur 6 colonnes KYC, 5 rôles applicatifs, audit automatique des opérations sensibles."

### Slide 6 : La migration en chiffres
Le tableau du bilan global.

### Slide 7 : La preuve de l'optimisation
Montrer un EXPLAIN PLAN, surligner "PARTITION RANGE ITERATOR" et "INDEX UNIQUE SCAN".

### Slide 8 : Les datamarts en action
Montrer un SELECT sur `mv_card_aggregates` ou `mv_mcc_aggregates` — vraies données, vrais chiffres.

### Slide 9 : L'audit en action
Montrer la requête de comptage du journal d'audit : 8 147 opérations tracées automatiquement.

### Slide 10 : Les difficultés résolues
Choisir 2-3 difficultés du tableau et raconter comment tu les as résolues. **C'est ici que tu marques le plus de points** : le jury veut entendre ta capacité d'analyse.

### Slide 11 : La suite (Sprint 2)
Présenter brièvement le plan pour MongoDB, Streaming, ML, etc. Montre que tu sais où tu vas.

---

## Démonstration en direct (si demandée par le jury)

Tu peux faire une démo bluffante en 3 minutes :

```bash
# 1. Compter les objets migrés (5 secondes)
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/bilan_migration.sql"

# 2. Montrer le chiffrement vivant (5 secondes)
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/demo_chiffrement.sql"

# 3. Lancer un EXPLAIN PLAN (30 secondes)
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/plan1.sql"

# 4. Montrer l'audit (5 secondes)
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/check_audit.sql"
```

Tu peux préparer ces 4 commandes dans un fichier `demo.sh` ou `demo.ps1` pour les enchaîner.

---

## Ce qui reste à faire (Sprint 2)

Pour information uniquement — non couvert par ce rapport :

- Brique NoSQL MongoDB
- Conteneurisation Docker Compose
- Streaming Kafka + Spark
- Orchestration Airflow
- Tests + CI/CD GitHub Actions
- Modèle ML enrichi
- API FastAPI complète
- Observabilité Prometheus / Grafana

Voir [`roadmap.md`](roadmap.md) pour le plan complet.

---

## Pour reproduire chez toi

Tout est expliqué dans le [README.md](../README.md) à la racine du repo. En 3 étapes :

```bash
# 1. Cloner
git clone https://github.com/MoumeWalter/finsecure-banking.git
cd finsecure-banking

# 2. Démarrer Oracle (Docker)
docker run -d --name oracle_db -p 1521:1521 -e ORACLE_PWD=password123 container-registry.oracle.com/database/express:latest
# ... attendre que la base soit prête (~3 min)

# 3. Exécuter le projet
.\setup.ps1  # Script tout-en-un (à créer en Phase suivante)
```

Compte 1h pour la mise en place + 6h pour la migration complète si on inclut le téléchargement du dataset.
