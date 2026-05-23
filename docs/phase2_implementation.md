# Phase 2 — Implémentation Oracle XE

## Vue d'ensemble

La Phase 2 traduit le modèle physique de la Phase 1 en **objets Oracle réels**,
opérationnels et sécurisés. Tous les choix sont alignés sur le cadrage client
(5 rôles applicatifs, conformité RGPD/ACPR, partitionnement pour la volumétrie).

## Livrables

### Scripts SQL (`sql/`)

| Fichier | Lignes | Objets créés |
|---|---|---|
| `00_init_users_tablespaces.sql` | 3 tablespaces, 2 schémas, 5 rôles, 5 comptes |
| `01_grants.sql` | Droits sur tables, vues, vues matérialisées |
| `02_sequences.sql` | 3 séquences pour IDs auto-générés |
| `03_tables.sql` | 9 tables avec PK/FK/CHECK/NN + partitionnement |
| `04_indexes.sql` | 11 index (B-tree, bitmap, composites, local) + statistiques |
| `05_views.sql` | 3 vues métier |
| `06_materialized_views.sql` | 3 datamarts matérialisés |
| `07_packages_plsql.sql` | 1 package, 4 procédures, 4 fonctions |
| `08_triggers.sql` | 5 triggers (3 audit + 2 auto-modification) |
| `09_explain_plans.sql` | 3 EXPLAIN PLAN des requêtes critiques |

### Code Python (`src/migration/`)

| Fichier | Rôle |
|---|---|
| `encryption.py` | Chiffrement AES-256-GCM des colonnes KYC sensibles |
| `load_oracle.py` | Migration multi-sources vers Oracle, par batchs, avec progress bar |

## Conformité au cadrage client

| Exigence du cadrage | Implémentation Phase 2 |
|---|---|
| 5 rôles applicatifs (admin, etl, data_scientist, analyst, audit) | `00_init_users_tablespaces.sql` + `01_grants.sql` |
| Chiffrement des données KYC sensibles | `encryption.py` (AES-256-GCM) + colonnes `_enc` |
| Traçabilité ACPR | Table `journal_audit` + 3 triggers d'audit |
| Volumétrie 22 M lignes | Partitionnement RANGE INTERVAL mensuel sur TRANSACTION |
| Performance des datamarts | 3 vues matérialisées + index dédiés |
| Séparation logique audit / métier | Tablespaces séparés (`ts_finsecure_data` vs `ts_finsecure_audit`) |
| Reproductibilité | Tous les scripts sont idempotents (CREATE OR REPLACE) |

## Stratégie d'optimisation Oracle

### Partitionnement

**Table** : `TRANSACTION` (22 M+ lignes)
**Type** : RANGE INTERVAL mensuel sur `situation_date`
**Bénéfice attendu** : partition pruning automatique sur tout filtre temporel.

Quand l'optimiseur voit `WHERE situation_date BETWEEN ... AND ...`, il **ne lit
que les partitions concernées** au lieu de scanner toute la table. Sur des
requêtes mensuelles, le gain est typiquement de x10 à x50.

### Index

**11 index** créés selon une stratégie ciblée :

1. **B-tree sur FK** : indispensable Oracle pour éviter les locks de table
   sur UPDATE/DELETE du parent.
2. **B-tree sur filtres temporels** : `date_transaction`, `date_operation`.
3. **Composite `(id_carte, situation_date)`** : sert les requêtes datamart
   du type "transactions d'une carte sur une période".
4. **Bitmap sur `is_fraud`** : très faible cardinalité (Y/N) = cas d'usage
   parfait pour bitmap, qui sera bien plus compact qu'un B-tree.
5. **LOCAL** sur la table partitionnée : les index sont eux-mêmes partitionnés,
   ce qui accélère les opérations de maintenance (DROP/EXCHANGE PARTITION).

### Vues matérialisées

Stratégie **REFRESH COMPLETE ON DEMAND** en V1 (simple, robuste).
Évolution prévue **REFRESH FAST** en V2 (incrémental, nécessite des
`materialized view logs` sur les tables source).

Le refresh est déclenché par :
- `BEGIN pkg_datamart.pr_refresh_all_datamarts; END;` (manuel)
- DAG Airflow quotidien (Sprint 2)

## EXPLAIN PLAN des 3 requêtes critiques

### Requête 1 : Top cartes du mois en cours

**Pattern attendu** :

```
PARTITION RANGE ITERATOR (pruning automatique sur situation_date)
  INDEX RANGE SCAN ix_transaction_carte_date
    HASH GROUP BY id_carte
      ORDER BY nb_tx DESC + FETCH FIRST 10 ROWS
```

**Sans partitionnement** : full scan de 22 M lignes.
**Avec partitionnement** : scan d'1 partition (~750k lignes), soit ~30x moins.

### Requête 2 : Détail d'une transaction enrichie

**Pattern attendu** :

```
INDEX UNIQUE SCAN pk_transaction (partition locale)
  NESTED LOOPS
    INDEX UNIQUE SCAN pk_carte
    INDEX UNIQUE SCAN pk_client
    INDEX UNIQUE SCAN pk_marchand
    INDEX UNIQUE SCAN pk_mcc
  HASH JOIN (LEFT OUTER) label_fraude
```

**Lecture** : 6 index lookups au lieu de full scans. Temps attendu < 5 ms.

### Requête 3 : Top catégories par fraude

**Pattern attendu** :

```
BITMAP INDEX SINGLE VALUE bx_label_is_fraud (filtre Y)
  HASH JOIN transaction
  HASH JOIN marchand
  HASH JOIN mcc
    HASH GROUP BY libelle_mcc
```

**Bénéfice** : l'index bitmap ne lit que les ~22 000 lignes is_fraud='Y' sur 8,9 M
labels, soit 0,25 % du volume. Sans bitmap, on aurait un full scan + filtre.

## Sécurité et conformité

### Chiffrement des colonnes sensibles

**Algorithme** : AES-256-GCM (authenticated encryption)
**Format de stockage** : base64(nonce || ciphertext) dans `VARCHAR2(255)`

Colonnes chiffrées :
- `client.address`
- `client.yearly_income`
- `client.total_debt`
- `client.per_capita_income`
- `carte.card_number_enc` (PAN)
- `carte.cvv_enc` (CVV)

Conformité :
- **RGPD article 32** (sécurisation des données personnelles) : ✅
- **PCI-DSS** (chiffrement du PAN et du CVV) : ✅
- **ACPR** (gestion des risques opérationnels) : ✅

### Audit applicatif

Trois triggers `AFTER INSERT OR UPDATE OR DELETE` alimentent `journal_audit` :

- `tr_client_audit` : trace toutes les modifications CLIENT
- `tr_carte_audit` : trace toutes les modifications CARTE (PAN/CVV jamais loggés !)
- `tr_utilisateur_si_audit` : trace toutes les modifications de comptes applicatifs

Les valeurs avant/après sont stockées au format JSON dans `CLOB`, ce qui
permet des requêtes d'audit ciblées :

```sql
SELECT date_operation, operation, valeur_avant, valeur_apres
FROM   journal_audit
WHERE  table_concernee = 'CLIENT'
  AND  id_ligne_concernee = 42
ORDER BY date_operation DESC;
```

### Principe du moindre privilège

Aucun rôle hors `role_admin` n'a `DROP`, `TRUNCATE`, `ALTER`. Les droits
sont strictement limités à ce que chaque persona doit faire dans son métier.

## Procédure d'exécution

Voir [`sql/README.md`](../sql/README.md) pour l'ordre des scripts et
[`src/migration/README.md`](../src/migration/README.md) pour la migration des données.

Procédure résumée :
1. Démarrer Oracle XE (Docker ou natif)
2. Exécuter les scripts SQL 00 → 08 dans l'ordre
3. Exécuter `01_grants.sql` en dernier (pour que les objets existent)
4. Configurer `.env` avec les credentials et la clé de chiffrement
5. Lancer `python -m src.migration.load_oracle --step all`
6. Refresh des datamarts : `BEGIN pkg_datamart.pr_refresh_all_datamarts; END;`
7. Exécuter `09_explain_plans.sql` pour capturer les plans d'exécution

## Conformité au Bloc 1 du RNCP36739

Cette implémentation démontre les **compétences attendues du Bloc 1** sur la
brique relationnelle :

| Compétence | Élément démontré |
|---|---|
| BDR adaptée au besoin client | 9 tables Merise, 5 rôles applicatifs, conformité RGPD/ACPR |
| Technologies et langages adaptés | Oracle XE, PL/SQL (package + procédures + fonctions + triggers), DDL/DCL |
| Stratégie d'indexation et de performance | 11 index, partitionnement, vues matérialisées, EXPLAIN PLAN |
| Sécurité | Rôles, GRANT/REVOKE, chiffrement AES-256, audit ACPR |
| Optimisation | Statistiques DBMS_STATS, plans d'exécution analysés |

## Évolutions Sprint 2

- Conteneurisation Oracle XE dans `docker/oracle.Dockerfile`
- Ordonnancement des refresh datamarts via Airflow
- Tests pytest sur `encryption.py` et `load_oracle.py`
- Migration en CI/CD : déploiement automatique des scripts SQL via GitHub Actions
- Mise en place de `materialized view logs` pour passer en REFRESH FAST
