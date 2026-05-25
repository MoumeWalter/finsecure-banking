# Scripts de demonstration

Ce dossier contient les requetes SQL pretes a executer pour valider la migration
et faire des demos au jury.

## Validation

- bilan_migration.sql      : Bilan complet (9 tables)
- check_audit.sql          : Detail des operations tracees par les triggers
- check_mv.sql             : Verification des datamarts (vues materialisees)
- check_partitions.sql     : Liste des partitions creees automatiquement

## Demos pour la soutenance

- demo_top_cards.sql       : Top 10 cartes les plus actives
- demo_top_mcc.sql         : Top 10 categories marchands
- demo_risque.sql          : Top 10 cartes a risque (taux de fraude eleve)
- refresh_datamarts.sql    : Recalcul des vues materialisees

## Plans d'execution (EXPLAIN PLAN)

- plan1.sql : Filtre temporel sur transactions (partition pruning)
- plan2.sql : Fraudes par MCC (jointures + index)
- plan3.sql : Lookup transaction par PK (index unique scan)

## Comment executer

Tous ces scripts sont a executer depuis le conteneur Docker oracle_db :

```bash
docker cp <script.sql> oracle_db:/tmp/
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/<script.sql>"
```
