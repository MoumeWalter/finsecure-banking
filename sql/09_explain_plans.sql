-- =============================================================================
-- 09_explain_plans.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Démonstration de l'optimisation Oracle via EXPLAIN PLAN sur 3 requêtes
-- représentatives du projet. Chaque requête est analysée pour démontrer
-- l'utilisation des index, du partitionnement et des stratégies de jointure.
--
-- Procédure :
--   1. EXPLAIN PLAN FOR <requête>
--   2. SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY) pour visualiser le plan
--   3. Captures à mettre dans docs/phase2_implementation.md
-- =============================================================================

SET LINESIZE 200
SET PAGESIZE 100

-- -----------------------------------------------------------------------------
-- REQUÊTE 1 : Top 10 cartes par nombre de transactions sur un mois
-- -----------------------------------------------------------------------------
-- Pattern attendu : Partition Pruning sur situation_date + INDEX RANGE SCAN
-- sur ix_transaction_carte_date + HASH GROUP BY
-- -----------------------------------------------------------------------------
PROMPT
PROMPT --- REQUÊTE 1 : Top 10 cartes du mois en cours ---
PROMPT

EXPLAIN PLAN FOR
SELECT  t.id_carte,
        COUNT(*)      AS nb_tx,
        SUM(t.amount) AS total_amount
FROM    transaction t
WHERE   t.situation_date BETWEEN
          TRUNC(SYSDATE, 'MM')
          AND LAST_DAY(SYSDATE)
GROUP BY t.id_carte
ORDER BY nb_tx DESC
FETCH FIRST 10 ROWS ONLY;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC +PARTITION +PREDICATE'));

-- -----------------------------------------------------------------------------
-- REQUÊTE 2 : Détail d'une transaction enrichie (lookup par PK)
-- -----------------------------------------------------------------------------
-- Pattern attendu : UNIQUE SCAN sur pk_transaction (LOCAL) + NESTED LOOPS
-- sur les autres tables via leurs index
-- -----------------------------------------------------------------------------
PROMPT
PROMPT --- REQUÊTE 2 : Détail d'une transaction enrichie ---
PROMPT

EXPLAIN PLAN FOR
SELECT  t.id_transaction,
        t.date_transaction,
        t.amount,
        cl.id_client,
        cl.credit_score,
        m.merchant_city,
        mcc.libelle_mcc,
        lf.is_fraud
FROM        transaction t
INNER JOIN  carte        c   ON t.id_carte    = c.id_carte
INNER JOIN  client       cl  ON c.id_client   = cl.id_client
INNER JOIN  marchand     m   ON t.id_marchand = m.id_marchand
INNER JOIN  mcc              ON m.code_mcc    = mcc.code_mcc
LEFT JOIN   label_fraude lf  ON t.id_transaction = lf.id_transaction
WHERE       t.id_transaction = 12345678;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC +PARTITION +PREDICATE'));

-- -----------------------------------------------------------------------------
-- REQUÊTE 3 : Agrégation par catégorie marchand sur les transactions frauduleuses
-- -----------------------------------------------------------------------------
-- Pattern attendu : INDEX FULL SCAN sur bx_label_is_fraud (bitmap)
-- + HASH JOIN + HASH GROUP BY
-- Cette requête prouve l'utilité de l'index bitmap sur is_fraud
-- -----------------------------------------------------------------------------
PROMPT
PROMPT --- REQUÊTE 3 : Top catégories marchandes par fraude ---
PROMPT

EXPLAIN PLAN FOR
SELECT  mcc.libelle_mcc,
        COUNT(*) AS nb_fraudes,
        SUM(t.amount) AS montant_fraude
FROM        label_fraude lf
INNER JOIN  transaction t   ON lf.id_transaction = t.id_transaction
INNER JOIN  marchand    m   ON t.id_marchand = m.id_marchand
INNER JOIN  mcc             ON m.code_mcc = mcc.code_mcc
WHERE       lf.is_fraud = 'Y'
GROUP BY    mcc.libelle_mcc
ORDER BY    nb_fraudes DESC
FETCH FIRST 20 ROWS ONLY;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(format => 'BASIC +PARTITION +PREDICATE'));

-- -----------------------------------------------------------------------------
-- MESURE DE PERFORMANCE EN CONDITIONS RÉELLES
-- -----------------------------------------------------------------------------
-- Une fois les données chargées (cf. src/migration/load_oracle.py), on peut
-- mesurer le temps réel d'exécution avec SET TIMING ON :
--
--   SET TIMING ON
--   SET AUTOTRACE ON EXPLAIN STATISTICS
--   <requête>
--   SET AUTOTRACE OFF
-- -----------------------------------------------------------------------------

PROMPT
PROMPT '09_explain_plans.sql terminé. Captures à inclure dans phase2_implementation.md.'
