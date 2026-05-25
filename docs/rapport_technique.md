# Rapport technique — FinSecure Banking

> Projet certifiant RNCP36739 — Expert en Ingénierie de Données
> M2 Data Engineering & IA — EFREI Paris Panthéon-Assas
> Auteur : Walter Moume — Version 2.0 (mai 2026)

---

## Table des matières

1. [Présentation du projet](#1-présentation-du-projet)
2. [Architecture cible](#2-architecture-cible)
3. [Sources de données](#3-sources-de-données)
4. [Modélisation Merise](#4-modélisation-merise)
5. [Implémentation Oracle XE](#5-implémentation-oracle-xe)
6. [Sécurité et conformité](#6-sécurité-et-conformité)
7. [Pipeline de migration](#7-pipeline-de-migration)
8. [Résultats et validation](#8-résultats-et-validation)
9. [Difficultés rencontrées et leçons apprises](#9-difficultés-rencontrées-et-leçons-apprises)
10. [Conformité aux exigences du Bloc 1](#10-conformité-aux-exigences-du-bloc-1)
11. [Évolutions Sprint 2](#11-évolutions-sprint-2)

---

## 1. Présentation du projet

### 1.1 Contexte client

**FinSecure Banking** est une banque de détail française fictive opérant sur le territoire métropolitain (1,2 M de clients, 4,5 M de transactions/jour). Le projet vise à moderniser sa plateforme de détection de fraude et de reporting réglementaire.

### 1.2 Problématique

L'existant souffre de quatre limitations majeures :

- **Données éclatées** entre systèmes legacy SQLite, extracts CSV/JSON et feuilles Excel
- **Détection de fraude tardive** (J+1, perte annuelle estimée 3,2 M€)
- **Pas de reporting consolidé** (5 jours ouvrés pour un rapport métier)
- **Risque réglementaire** sur la conformité ACPR (traçabilité) et RGPD (durée de conservation, droit à l'oubli)

### 1.3 Objectifs métier et techniques

| ID | Objectif | KPI cible |
|---|---|---|
| O1 | Consolider toutes les sources transactionnelles | 100 % intégrées |
| O2 | Détecter la fraude en temps quasi-réel (Sprint 2) | Latence ≤ 5 s |
| O3 | Réduire le délai de production des rapports | ≤ 4 h |
| O4 | Garantir la conformité RGPD/ACPR | 100 % données sensibles chiffrées + traçabilité complète |
| T1 | Stockage scalable | OK 22 M lignes, extensible à 100 M |
| T2 | API REST exposant les datamarts (Sprint 2) | Disponibilité > 99 %, latence P95 < 500 ms |
| T3 | Pipeline reproductible et ordonnancé (Sprint 2) | DAG Airflow vert ≥ 99 % |

---

## 2. Architecture cible

Le projet implémente une architecture **polyglot persistence** moderne en quatre couches :

1. **Sources** : SQLite legacy + CSV + JSON
2. **Datalake médaillon** : Bronze (raw) → Silver (nettoyé) → Gold (datamarts) en Parquet sur Hive
3. **Stockages métier** : Oracle XE (source de vérité relationnelle) + MongoDB (documents enrichis)
4. **Consommation** : Power BI + API FastAPI + Spark MLlib

Le présent rapport documente l'implémentation **Oracle XE** (cœur du Bloc 1). Les autres briques sont prévues dans le Sprint 2.

Voir le schéma complet dans [`docs/architecture_cible.svg`](architecture_cible.svg).

---

## 3. Sources de données

Le projet exploite un dataset bancaire synthétique de production-grade :

| Source | Format | Volumétrie réelle | Description |
|---|---|---|---|
| `transactions_data.csv` | CSV | **13 305 915 lignes** | Transactions bancaires historiques |
| `users_data.csv` | CSV | 2 000 lignes | Données KYC clients |
| `cards_data.csv` | CSV | 6 146 lignes | Cartes bancaires |
| `mcc_codes.json` | JSON | 109 entrées | Codes ISO 18245 |
| `train_fraud_labels.json` | JSON | 8 914 963 labels | Étiquettes Yes/No pour ML |

**Note méthodologique** : la documentation initiale annonçait 22 M de transactions. L'inspection réelle a révélé 13,3 M. La cohérence interne du dataset est parfaite (aucune perte de FK lors de l'ingestion, malgré la jointure entre 13,3 M transactions et 8,9 M labels).

---

## 4. Modélisation Merise

### 4.1 Démarche

La modélisation suit la démarche Merise classique en trois temps :

- **MCD** : 9 entités identifiées, indépendantes de toute technologie
- **MLD** : traduction normalisée en 3NF
- **MPD** : adaptation Oracle XE avec types, partitionnement, index

Voir [`docs/data_model/modele_donnees.md`](data_model/modele_donnees.md) pour le détail complet.

### 4.2 Entités principales

| Catégorie | Entités |
|---|---|
| **Métier principal** | CLIENT, CARTE |
| **Référentiels et événements** | MARCHAND, MCC, TRANSACTION, LABEL_FRAUDE, ERREUR_TRANSACTION |
| **Technique (audit)** | UTILISATEUR_SI, JOURNAL_AUDIT |

### 4.3 Décisions de modélisation argumentées

Cinq décisions ont été prises et justifiées :

1. **Table `ERREUR_TRANSACTION` dédiée** plutôt que colonne multi-valuée → conformité 1NF
2. **Table `MARCHAND` dérivée par déduplication** depuis les transactions → conformité 3NF, élimination de redondance
3. **Pas d'historisation SCD2 sur CLIENT** → trade-off complexité/valeur, dataset sans snapshots multi-périodes
4. **Chiffrement applicatif AES-256** sur les colonnes sensibles → conformité RGPD article 32, PCI-DSS
5. **Colonne `situation_date` matérialisée** dans TRANSACTION → indispensable au partitionnement RANGE INTERVAL

### 4.4 Vérification des formes normales

| Forme normale | Vérification |
|---|---|
| **1NF** — atomicité | OK (éclatement de la colonne `errors`) |
| **2NF** — dépendance complète à la clé | OK (toutes les PK sont mono-colonne) |
| **3NF** — pas de dépendance transitive | OK (vérifié sur les cas à risque : MARCHAND/MCC, TRANSACTION/MARCHAND) |

---

## 5. Implémentation Oracle XE

### 5.1 Choix technologique

**Oracle XE 21c** a été retenu pour quatre raisons documentées dans [`docs/veille_technologique.md`](veille_technologique.md) :

- Standard du secteur bancaire français
- PL/SQL avancé (packages, procédures, fonctions, triggers)
- Partitionnement INTERVAL natif et flexible
- Conteneurisable (image officielle Docker)

### 5.2 Structure physique

**3 tablespaces** isolés pour séparer les I/O et le cycle de vie :

- `ts_finsecure_data` (8 Go max) — données métier
- `ts_finsecure_idx` (2 Go max) — index (séparation physique)
- `ts_finsecure_audit` (4 Go max) — journal d'audit (cycle de vie distinct)

### 5.3 Tables (9)

Toutes créées avec :
- Clés primaires et étrangères
- Contraintes CHECK adaptées (relaxées après inspection des données réelles)
- Commentaires métier sur chaque table et colonne
- `date_creation` automatique via DEFAULT SYSTIMESTAMP

### 5.4 Partitionnement

**Table `TRANSACTION` partitionnée RANGE INTERVAL** sur `situation_date` :

```sql
PARTITION BY RANGE (situation_date)
INTERVAL (NUMTOYMINTERVAL(1, 'MONTH'))
(
  PARTITION p_initial VALUES LESS THAN (TO_DATE('2024-01-01', 'YYYY-MM-DD'))
);
```

**Résultat à la migration** : Oracle a créé automatiquement la partition `SYS_P987` au premier INSERT de mai 2026, sans intervention manuelle. C'est la démonstration en action de la fonctionnalité.

### 5.5 Index (12)

Stratégie d'indexation ciblée :

- **6 index B-tree sur FK** : `id_client`, `code_mcc`, `id_carte`, `id_marchand`, `id_transaction`, `id_utilisateur`
- **2 index temporels** : `date_transaction`, `date_operation`
- **1 index composite** : `(id_carte, situation_date)` pour les requêtes datamart
- **1 index BITMAP** sur `is_fraud` (faible cardinalité Y/N)
- **1 index sur code_erreur** (agrégations par type)
- **Index LOCAL** sur la table partitionnée (maintenance facilitée)

Statistiques DBMS_STATS calculées après chargement.

### 5.6 Vues (3) + Vues matérialisées (3)

**Vues classiques** :

- `v_transactions_enrichies` : jointure complète tx + carte + client + marchand + MCC + label
- `v_clients_avec_cartes` : synthèse par client
- `v_marchands_par_volume` : classement marchands

**Vues matérialisées (datamarts Gold)** :

- `mv_card_aggregates` (4 071 lignes) : agrégats par carte
- `mv_daily_aggregates` (1 ligne) : agrégats journaliers
- `mv_mcc_aggregates` (109 lignes) : agrégats par catégorie marchand

Refresh COMPLETE ON DEMAND via le package PL/SQL.

### 5.7 PL/SQL — Package `pkg_datamart`

Architecture en package pour la maintenabilité :

| Type | Nom | Rôle |
|---|---|---|
| Constante | `c_seuil_fraude_alerte` | Seuil métier d'alerte (5 %) |
| Procédure | `pr_refresh_card_aggregates` | Refresh du datamart cartes |
| Procédure | `pr_refresh_daily_aggregates` | Refresh du datamart journalier |
| Procédure | `pr_refresh_mcc_aggregates` | Refresh du datamart MCC |
| Procédure | `pr_refresh_all_datamarts` | Refresh global |
| Procédure | `pr_charger_marchands` | Stub pour ingestion SQL alternative |
| Fonction | `fn_calc_taux_fraude_carte` | Taux de fraude d'une carte |
| Fonction | `fn_calc_score_risque_client` | Score composite de risque |
| Fonction | `fn_get_libelle_mcc` | Lookup MCC |
| Fonction | `fn_carte_a_risque` | Indicateur Y/N selon seuil |

### 5.8 Triggers (5)

| Trigger | Table | Évènement | Rôle |
|---|---|---|---|
| `tr_client_audit` | CLIENT | INSERT/UPDATE/DELETE | Trace ACPR/RGPD |
| `tr_carte_audit` | CARTE | INSERT/UPDATE/DELETE | Trace ACPR/RGPD (sans PAN/CVV !) |
| `tr_utilisateur_si_audit` | UTILISATEUR_SI | INSERT/UPDATE/DELETE | Trace gestion comptes |
| `tr_client_modif_date` | CLIENT | BEFORE UPDATE | Auto-update `date_modification` |
| `tr_carte_modif_date` | CARTE | BEFORE UPDATE | Auto-update `date_modification` |

---

## 6. Sécurité et conformité

### 6.1 Modèle de rôles (5)

| Rôle | Périmètre |
|---|---|
| `role_admin` | Tous droits sur les tables métier |
| `role_etl` | SELECT/INSERT/UPDATE/DELETE sur métier, SELECT audit |
| `role_data_scientist` | SELECT sur métier et vues |
| `role_analyst` | SELECT sur vues matérialisées uniquement |
| `role_audit` | SELECT sur JOURNAL_AUDIT uniquement |

Application stricte du principe **least privilege**. Aucun rôle hors `admin` ne dispose de DROP, TRUNCATE ou ALTER.

### 6.2 Chiffrement AES-256-GCM

**Implémentation** : module Python `src/migration/encryption.py` utilisant `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.

**Colonnes chiffrées** (6) :

- `client.address`
- `client.per_capita_income`
- `client.yearly_income`
- `client.total_debt`
- `carte.card_number_enc` (PAN)
- `carte.cvv_enc` (CVV)

**Format de stockage** : `base64(nonce_12bytes || ciphertext)` dans VARCHAR2(255).

**Validation en production** : sur 2 000 clients migrés, les 4 colonnes KYC sont stockées en ciphertext base64 dans Oracle, vérifié par requête SQL. Le déchiffrement aller-retour fonctionne via le module Python.

### 6.3 Audit ACPR/RGPD

Le système a tracé **automatiquement 8 147 opérations** sensibles pendant la migration, sans aucune intervention applicative :

| Table | Opération | Nombre |
|---|---|---|
| CARTE | INSERT | 6 146 |
| CLIENT | INSERT | 2 000 |
| UTILISATEUR_SI | INSERT | 1 |

Chaque entrée d'audit contient : utilisateur (mappé via Oracle USER), table concernée, opération, valeurs avant/après en JSON (CLOB), horodatage.

**Point sécurité critique** : les triggers d'audit n'enregistrent **jamais** les valeurs sensibles (PAN, CVV), même chiffrées, dans le journal d'audit. Conformité PCI-DSS respectée.

---

## 7. Pipeline de migration

### 7.1 Architecture

Pipeline Python organisé en `src/migration/load_oracle.py` :

- Connexion `oracledb` en mode thin (sans Oracle Client lourd)
- Lecture multi-format (CSV pandas, JSON natif, SQLite legacy)
- Chiffrement à la volée des colonnes KYC sensibles
- Insertion massive par batchs (`executemany`, 10 000 lignes/batch)
- Gestion des types Pandas (NaN → None pour VARCHAR2)
- Lecture chunked pour les gros CSV (chunks de 100 000 ou 500 000 lignes)
- Logs structurés + progress bars `tqdm`

### 7.2 Étapes de migration (7 phases)

| Étape | Volume | Durée mesurée |
|---|---|---|
| MCC | 109 | < 1 s |
| Clients (chiffrement KYC) | 2 000 | 1 s |
| Cartes (chiffrement PAN/CVV) | 6 146 | 1 s |
| Marchands (déduplication 13M) | 74 831 | 5 min |
| **Transactions** | **13 305 915** | **5 h** |
| Labels de fraude | 8 914 963 | 4 min |
| Erreurs (éclatement 1NF) | 212 335 | 29 min |
| **Total objets** | **22 533 698** | **~5 h 40** |

### 7.3 Refresh des datamarts

Une fois la migration terminée, un appel à `pkg_datamart.pr_refresh_all_datamarts` recalcule les trois vues matérialisées. Durée mesurée : ~10 minutes.

---

## 8. Résultats et validation

### 8.1 Bilan global migré

```
NOM_TABLE              NB_LIGNES
------------------     ----------
MCC                           109
CLIENT                      2 000
CARTE                       6 146
MARCHAND                   74 831
TRANSACTION            13 305 915
LABEL_FRAUDE            8 914 963
ERREUR_TRANSACTION        212 335
UTILISATEUR_SI                  2
JOURNAL_AUDIT               8 147
                       ----------
TOTAL                  22 533 698
```

Espace disque utilisé : **9,7 Go** sur les 12 Go de la limite Oracle XE.

### 8.2 Analyses métier découvertes

**Top catégories par volume** :

| Catégorie | Transactions | Montant total |
|---|---|---|
| Grocery Stores | 1 592 584 | 40,9 M$ |
| Miscellaneous Food | 1 460 875 | 15,5 M$ |
| Service Stations | 1 424 711 | 29,5 M$ |
| Eating Places | 999 738 | 26,3 M$ |
| Drug Stores | 772 913 | 35,1 M$ |

**Top cartes à risque** (>100 transactions, par taux de fraude) :

| Carte | Tx | Fraudes | Taux |
|---|---|---|---|
| 3066 | 129 | 14 | **10,85 %** |
| 4068 | 182 | 10 | 5,49 % |
| 3697 | 695 | 34 | 4,89 % |

Ces 4 071 cartes actives (sur 6 146 émises) génèrent l'essentiel du volume — info opérationnelle pour le département Risque.

### 8.3 EXPLAIN PLAN sur 3 requêtes critiques

Voir [`docs/plan1_partitionnement.txt`](plan1_partitionnement.txt), [`docs/plan2_jointures.txt`](plan2_jointures.txt), [`docs/plan3_lookup_pk.txt`](plan3_lookup_pk.txt) pour les plans détaillés.

**Synthèse** :

| Requête | Optimisation prouvée |
|---|---|
| Filtre temporel | `PARTITION RANGE ITERATOR` — partition pruning automatique |
| Top fraudes par MCC | 4 `NESTED LOOPS` via index → aucun full scan non maîtrisé |
| Lookup transaction par PK | 5 `INDEX UNIQUE SCAN` en cascade → temps constant |

---

## 9. Difficultés rencontrées et leçons apprises

Cette section documente les **vrais retours d'expérience** acquis pendant l'implémentation. Ils sont valorisables car ils correspondent aux problématiques réelles d'ingénierie data.

### 9.1 Bootstrap des triggers d'audit

**Problème** : le trigger `tr_utilisateur_si_audit` insère dans `JOURNAL_AUDIT` qui a une FK vers `UTILISATEUR_SI`. Au moment du tout premier INSERT, la table n'a aucun utilisateur, donc la FK explose (cas œuf et poule classique).

**Solution** : désactivation temporaire du trigger pour insérer un compte SYSTEM (id=0), puis réactivation. Stratégie documentée et reproductible.

### 9.2 Partitionnement et clé primaire

**Problème initial** : DDL `CONSTRAINT pk_transaction PRIMARY KEY (id_transaction) USING INDEX LOCAL`. Oracle a refusé : `ORA-14039 partitioning columns must form a subset of key columns of a UNIQUE index`.

**Cause** : avec `USING INDEX LOCAL`, Oracle exige que la colonne de partitionnement (`situation_date`) fasse partie de la PK. Or notre PK est sur `id_transaction` seul.

**Solution** : suppression de `USING INDEX LOCAL`, ce qui force un index GLOBAL pour la PK. Compatible avec le partitionnement.

### 9.3 Contraintes CHECK trop strictes vs données réelles

Plusieurs contraintes définies à la modélisation se sont révélées trop strictes face aux données :

- **`UQ_MCC_LIBELLE`** : le standard ISO 18245 contient légitimement des doublons (ex. "Passenger Railways" sur 2 codes). UNIQUE supprimée.
- **`CK_CARTE_TYPE`** acceptait `'Debit Prepaid'` mais les données contenaient `'Debit (Prepaid)'`. Constraint relaxée.
- **`CK_CLIENT_INCOME_POS`** vérifiait `yearly_income >= 0` mais cette colonne est devenue VARCHAR2 (chiffrée). Constraint supprimée.

**Leçon** : la définition des contraintes doit se faire en deux temps — modélisation théorique, puis ajustement après inspection des données réelles. En V2, un système Great Expectations validera les données EN AMONT de l'INSERT.

### 9.4 Types pandas et Oracle

**Problème** : `oracledb` refuse `float('nan')` (NaN pandas) pour une colonne VARCHAR2. Le 28e chunk a planté après 4 minutes de scan.

**Solution** : helpers défensifs `s(value)`, `i(value)`, `f(value)` qui convertissent NaN en None. Application systématique sur toutes les colonnes texte.

### 9.5 Encodage UTF-8 vs SQL*Plus

Plusieurs scripts créés via PowerShell avaient un BOM UTF-8 qui faisait apparaître un caractère parasite en début de fichier. SQL*Plus l'a toujours ignoré, mais le warning `SP2-0734: unknown command` s'affichait. Migration vers `-Encoding ascii` dans PowerShell pour les scripts SQL ultérieurs.

### 9.6 Performances Oracle XE

5 heures pour 13,3 M de transactions = ~740 inserts/seconde en moyenne. C'est honnête sur XE avec sa limite de 2 Go de RAM et la maintenance simultanée de 4 index + 1 trigger d'audit. Sur Oracle Enterprise ou Oracle Cloud, on serait à 10x cette vitesse. À noter pour la soutenance comme limitation de la version Express.

---

## 10. Conformité aux exigences du Bloc 1

| Compétence du Bloc 1 RNCP36739 | Démonstration |
|---|---|
| BDR adaptée au besoin client | 9 tables Merise, 5 rôles applicatifs cohérents avec le cadrage |
| Technologies et langages adaptés | Oracle XE 21c, PL/SQL, DDL/DCL/DML |
| Modélisation MCD/MLD/MPD | Documents complets dans `docs/data_model/` |
| Normalisation et choix justifiés | 3NF vérifiée + 5 décisions documentées |
| Stratégie d'indexation et performance | 12 index, partitionnement INTERVAL, vues matérialisées, EXPLAIN PLAN prouvés |
| Sécurité | 5 rôles avec least privilege, chiffrement AES-256 vérifié |
| Auditabilité | 8 147 opérations tracées automatiquement, conformité ACPR/RGPD |

**Au-delà des exigences**, le projet démontre aussi :

- Une **migration réelle** de plus de 22 millions d'objets, validée bout-en-bout
- Une **inspection des données** ayant conduit à l'ajustement raisonné de contraintes
- Une **méthodologie itérative** documentée (5 décisions argumentées, 6 difficultés résolues)

---

## 11. Évolutions Sprint 2

Le Sprint 1 (Phase 1 + Phase 2) constitue le socle relationnel du Bloc 1. Le Sprint 2 enrichira :

- **Phase 3** : Base NoSQL MongoDB (compétence Bloc 1 — NoSQL)
- **Phase 5** : Conteneurisation Docker Compose multi-services
- **Phase 6** : Streaming Kafka + Spark Structured Streaming (compétence Bloc 2 — Big Data)
- **Phase 7** : Orchestration Airflow
- **Phase 8** : Tests Pytest + Great Expectations (couverture 70 %)
- **Phase 9** : CI/CD GitHub Actions
- **Phase 10** : ML Spark MLlib avec MLflow + gestion du déséquilibre de classes
- **Phase 11** : API FastAPI enrichie avec POST /predict + JWT
- **Phase 12** : Observabilité Prometheus + Grafana
- **Phase 13** : Documentation finale et rapport de soutenance

Avec ces phases, le projet couvrira intégralement les Blocs 1 et 2 du RNCP36739, et fournira des éléments pour les Blocs 3 (Cloud), 4 (Data Science) et 5 (Gouvernance).

---

## Annexes

- [Cadrage client détaillé](cadrage_client.md)
- [Architecture cible (schéma SVG)](architecture_cible.svg)
- [Veille technologique](veille_technologique.md)
- [Modèle de données complet](data_model/modele_donnees.md)
- [Dictionnaire de données](data_model/dictionnaire_donnees.md)
- [Plans d'exécution Oracle](.)
- [Code source migration](../src/migration/)
- [Scripts SQL](../sql/)

---

**Auteur** : Walter Moume — `walter.moume@example.fr`
**Repository** : https://github.com/MoumeWalter/finsecure-banking
**Licence** : MIT
