# Scripts SQL — Implémentation Oracle XE

## Ordre d'exécution

Les scripts doivent être exécutés **dans l'ordre numérique**. Chaque script
indique en tête le compte sous lequel il doit être lancé.

| Étape | Script | Compte | Description |
|---|---|---|---|
| 1 | `00_init_users_tablespaces.sql` | `SYS AS SYSDBA` | Tablespaces, schémas, rôles, comptes |
| 2 | `02_sequences.sql` | `FINSECURE` | Séquences pour IDs auto-générés |
| 3 | `03_tables.sql` | `FINSECURE` | 9 tables avec contraintes + partitionnement |
| 4 | `04_indexes.sql` | `FINSECURE` | Index B-tree, bitmap, composites + statistiques |
| 5 | `05_views.sql` | `FINSECURE` | 3 vues métier |
| 6 | `06_materialized_views.sql` | `FINSECURE` | 3 datamarts (vues matérialisées) |
| 7 | `07_packages_plsql.sql` | `FINSECURE` | Package `pkg_datamart` |
| 8 | `08_triggers.sql` | `FINSECURE` | 5 triggers (audit + auto-update) |
| 9 | `01_grants.sql` | `FINSECURE` | Attribution des droits aux rôles |
| 10 | `09_explain_plans.sql` | `FINSECURE` | Plans d'exécution des 3 requêtes critiques |

> **Note** : `01_grants.sql` est numéroté avant `02_sequences.sql` pour la lisibilité,
> mais son exécution doit avoir lieu **après tous les autres scripts** car il
> référence des objets (tables, vues, vues matérialisées) qui doivent exister.

## Exécution rapide via SQL*Plus

```bash
# Connexion SYS
sqlplus sys/<password>@//localhost:1521/XEPDB1 as sysdba
SQL> @sql/00_init_users_tablespaces.sql
SQL> exit

# Connexion FINSECURE
sqlplus finsecure/<password>@//localhost:1521/XEPDB1
SQL> @sql/02_sequences.sql
SQL> @sql/03_tables.sql
SQL> @sql/04_indexes.sql
SQL> @sql/05_views.sql
SQL> @sql/06_materialized_views.sql
SQL> @sql/07_packages_plsql.sql
SQL> @sql/08_triggers.sql
SQL> @sql/01_grants.sql
SQL> @sql/09_explain_plans.sql
SQL> exit
```

## Exécution via Docker

Si Oracle XE tourne dans Docker (`oracle-db` est le nom du conteneur) :

```bash
# Copier les scripts dans le conteneur
docker cp sql/ oracle-db:/tmp/sql/

# Exécuter chaque script
docker exec -it oracle-db bash -c "
  sqlplus sys/<password>@//localhost:1521/XEPDB1 as sysdba @/tmp/sql/00_init_users_tablespaces.sql
"
docker exec -it oracle-db bash -c "
  sqlplus finsecure/<password>@//localhost:1521/XEPDB1 @/tmp/sql/02_sequences.sql
"
# ... etc
```

Un script `docker/run_sql.sh` est fourni en Phase 5 (Sprint 2) pour automatiser ces étapes.

## Vérification

Après exécution complète, lancer la requête suivante (en tant que `FINSECURE`) :

```sql
SELECT object_type, COUNT(*) AS nb
FROM   user_objects
GROUP BY object_type
ORDER BY object_type;
```

Résultat attendu :

| OBJECT_TYPE | NB |
|---|---|
| FUNCTION | 1 |
| INDEX | 11 |
| MATERIALIZED VIEW | 3 |
| PACKAGE | 1 |
| PACKAGE BODY | 1 |
| SEQUENCE | 4 |
| TABLE | 9 |
| TABLE PARTITION | 1+ |
| TRIGGER | 5 |
| VIEW | 3 |

Si tous ces objets existent, la base est prête pour la migration des données.

## Rollback complet

Pour repartir à zéro (DESTRUCTIF) :

```sql
-- En tant que SYS
DROP USER finsecure CASCADE;
DROP USER finsecure_audit CASCADE;
DROP USER usr_admin CASCADE;
DROP USER usr_etl CASCADE;
DROP USER usr_datascience CASCADE;
DROP USER usr_analyst CASCADE;
DROP USER usr_audit CASCADE;
DROP ROLE role_admin;
DROP ROLE role_etl;
DROP ROLE role_data_scientist;
DROP ROLE role_analyst;
DROP ROLE role_audit;
DROP TABLESPACE ts_finsecure_data    INCLUDING CONTENTS AND DATAFILES;
DROP TABLESPACE ts_finsecure_idx     INCLUDING CONTENTS AND DATAFILES;
DROP TABLESPACE ts_finsecure_audit   INCLUDING CONTENTS AND DATAFILES;
```
