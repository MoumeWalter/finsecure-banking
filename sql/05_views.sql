-- =============================================================================
-- 05_views.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Vues simples pour simplifier l'écriture des requêtes utilisateurs.
-- Ces vues NE sont PAS matérialisées : elles sont recalculées à chaque appel.
-- Pour les usages BI/datamart, voir 06_materialized_views.sql.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- v_transactions_enrichies
-- -----------------------------------------------------------------------------
-- Vue "tout-en-un" : transaction + carte + client + marchand + MCC + label
-- Sert pour l'export ad hoc, le debug et le ML
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_transactions_enrichies AS
SELECT
  t.id_transaction,
  t.date_transaction,
  t.amount,
  t.use_chip,
  t.situation_date,
  -- Carte
  c.id_carte,
  c.card_brand,
  c.card_type,
  c.has_chip,
  c.credit_limit,
  c.card_on_dark_web,
  -- Client
  cl.id_client,
  cl.current_age,
  cl.gender,
  cl.credit_score,
  -- Marchand
  m.id_marchand,
  m.merchant_city,
  m.merchant_state,
  m.zip,
  -- MCC
  mcc.code_mcc,
  mcc.libelle_mcc,
  -- Label fraude (peut être NULL : LEFT JOIN)
  lf.is_fraud
FROM        transaction      t
INNER JOIN  carte            c   ON t.id_carte    = c.id_carte
INNER JOIN  client           cl  ON c.id_client   = cl.id_client
INNER JOIN  marchand         m   ON t.id_marchand = m.id_marchand
INNER JOIN  mcc                  ON m.code_mcc    = mcc.code_mcc
LEFT  JOIN  label_fraude     lf  ON t.id_transaction = lf.id_transaction;

COMMENT ON TABLE v_transactions_enrichies IS
  'Vue dénormalisée des transactions avec tout le contexte (carte, client, marchand, MCC, label)';

-- -----------------------------------------------------------------------------
-- v_clients_avec_cartes
-- -----------------------------------------------------------------------------
-- Agrégat par client : nb de cartes, plafond total, présence dark web
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_clients_avec_cartes AS
SELECT
  cl.id_client,
  cl.current_age,
  cl.gender,
  cl.credit_score,
  COUNT(c.id_carte)                                    AS nb_cartes,
  SUM(c.credit_limit)                                  AS plafond_total,
  SUM(CASE WHEN c.card_on_dark_web = 'Y' THEN 1 ELSE 0 END) AS nb_cartes_dark_web
FROM        client cl
LEFT JOIN   carte  c ON cl.id_client = c.id_client
GROUP BY    cl.id_client, cl.current_age, cl.gender, cl.credit_score;

COMMENT ON TABLE v_clients_avec_cartes IS
  'Synthèse par client : nombre de cartes, plafond cumulé, exposition dark web';

-- -----------------------------------------------------------------------------
-- v_marchands_par_volume
-- -----------------------------------------------------------------------------
-- Classement des marchands par volume de transactions
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_marchands_par_volume AS
SELECT
  m.id_marchand,
  m.merchant_city,
  m.merchant_state,
  mcc.libelle_mcc,
  COUNT(t.id_transaction) AS nb_transactions,
  SUM(t.amount)           AS montant_total,
  AVG(t.amount)           AS montant_moyen
FROM        marchand    m
INNER JOIN  mcc             ON m.code_mcc = mcc.code_mcc
LEFT JOIN   transaction t   ON m.id_marchand = t.id_marchand
GROUP BY    m.id_marchand, m.merchant_city, m.merchant_state, mcc.libelle_mcc;

COMMENT ON TABLE v_marchands_par_volume IS
  'Classement des marchands par volume de transactions et montant';

-- -----------------------------------------------------------------------------
-- Grants pour role_analyst (lecture des vues)
-- -----------------------------------------------------------------------------
GRANT SELECT ON v_transactions_enrichies TO role_analyst;
GRANT SELECT ON v_clients_avec_cartes    TO role_analyst;
GRANT SELECT ON v_marchands_par_volume   TO role_analyst;

GRANT SELECT ON v_transactions_enrichies TO role_data_scientist;
GRANT SELECT ON v_clients_avec_cartes    TO role_data_scientist;
GRANT SELECT ON v_marchands_par_volume   TO role_data_scientist;

PROMPT '05_views.sql terminé avec succès. 3 vues créées.'
