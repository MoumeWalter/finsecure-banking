-- =============================================================================
-- 06_materialized_views.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Vues matérialisées = équivalent SQL des datamarts Gold du datalake.
-- Stockage physique du résultat de la requête, rafraîchi à la demande
-- via DBMS_MVIEW.REFRESH (appelé par Airflow en Sprint 2).
--
-- Stratégie : REFRESH COMPLETE en V1 (simple), à upgrader en FAST en V2
-- (nécessite des materialized view logs sur les tables source).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- mv_card_aggregates : agrégats par carte bancaire
-- -----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_card_aggregates
  TABLESPACE ts_finsecure_data
  BUILD IMMEDIATE
  REFRESH COMPLETE ON DEMAND
  ENABLE QUERY REWRITE
AS
SELECT
  t.id_carte,
  COUNT(t.id_transaction)                                          AS nb_transactions,
  ROUND(SUM(t.amount), 2)                                          AS total_amount,
  ROUND(AVG(t.amount), 2)                                          AS avg_amount,
  SUM(CASE WHEN lf.is_fraud = 'Y' THEN 1 ELSE 0 END)               AS nb_fraudes,
  ROUND(
    SUM(CASE WHEN lf.is_fraud = 'Y' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(t.id_transaction), 0)
  , 4)                                                             AS taux_fraude_pct
FROM       transaction t
LEFT JOIN  label_fraude lf ON t.id_transaction = lf.id_transaction
GROUP BY   t.id_carte;

COMMENT ON MATERIALIZED VIEW mv_card_aggregates IS
  'Datamart par carte (équivalent SQL de gold.card_aggregates côté Hive)';

CREATE UNIQUE INDEX ux_mv_card_aggregates_id_carte
  ON mv_card_aggregates(id_carte)
  TABLESPACE ts_finsecure_idx;

-- -----------------------------------------------------------------------------
-- mv_daily_aggregates : agrégats par jour
-- -----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_daily_aggregates
  TABLESPACE ts_finsecure_data
  BUILD IMMEDIATE
  REFRESH COMPLETE ON DEMAND
  ENABLE QUERY REWRITE
AS
SELECT
  t.situation_date,
  COUNT(t.id_transaction)                                          AS nb_tx,
  ROUND(SUM(t.amount), 2)                                          AS total_amount,
  ROUND(AVG(t.amount), 2)                                          AS avg_amount,
  SUM(CASE WHEN lf.is_fraud = 'Y' THEN 1 ELSE 0 END)               AS nb_fraudes,
  ROUND(
    SUM(CASE WHEN lf.is_fraud = 'Y' THEN 1 ELSE 0 END) * 100.0
    / NULLIF(COUNT(t.id_transaction), 0)
  , 4)                                                             AS taux_fraude_pct
FROM       transaction t
LEFT JOIN  label_fraude lf ON t.id_transaction = lf.id_transaction
GROUP BY   t.situation_date;

COMMENT ON MATERIALIZED VIEW mv_daily_aggregates IS
  'Datamart journalier (équivalent SQL de gold.daily_aggregates côté Hive)';

CREATE UNIQUE INDEX ux_mv_daily_aggregates_date
  ON mv_daily_aggregates(situation_date)
  TABLESPACE ts_finsecure_idx;

-- -----------------------------------------------------------------------------
-- mv_mcc_aggregates : agrégats par catégorie marchand (BONUS Marketing)
-- -----------------------------------------------------------------------------
CREATE MATERIALIZED VIEW mv_mcc_aggregates
  TABLESPACE ts_finsecure_data
  BUILD IMMEDIATE
  REFRESH COMPLETE ON DEMAND
  ENABLE QUERY REWRITE
AS
SELECT
  mcc.code_mcc,
  mcc.libelle_mcc,
  COUNT(t.id_transaction)            AS nb_transactions,
  ROUND(SUM(t.amount), 2)            AS total_amount,
  ROUND(AVG(t.amount), 2)            AS avg_amount,
  COUNT(DISTINCT t.id_carte)         AS nb_cartes_uniques
FROM       transaction t
INNER JOIN marchand m  ON t.id_marchand = m.id_marchand
INNER JOIN mcc            ON m.code_mcc = mcc.code_mcc
GROUP BY   mcc.code_mcc, mcc.libelle_mcc;

COMMENT ON MATERIALIZED VIEW mv_mcc_aggregates IS
  'Datamart par catégorie marchand pour le département Marketing';

CREATE UNIQUE INDEX ux_mv_mcc_aggregates_code
  ON mv_mcc_aggregates(code_mcc)
  TABLESPACE ts_finsecure_idx;

-- -----------------------------------------------------------------------------
-- Grants aux rôles analyst et data_scientist
-- -----------------------------------------------------------------------------
GRANT SELECT ON mv_card_aggregates  TO role_analyst, role_data_scientist;
GRANT SELECT ON mv_daily_aggregates TO role_analyst, role_data_scientist;
GRANT SELECT ON mv_mcc_aggregates   TO role_analyst, role_data_scientist;

PROMPT '06_materialized_views.sql terminé avec succès. 3 datamarts créés.'
