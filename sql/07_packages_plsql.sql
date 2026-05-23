-- =============================================================================
-- 07_packages_plsql.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Package pkg_datamart regroupant la logique métier réutilisable :
--   - Procédures de refresh des vues matérialisées
--   - Procédure de chargement de la dimension MARCHAND par DISTINCT
--   - Fonctions de calcul d'indicateurs métier
-- =============================================================================

-- -----------------------------------------------------------------------------
-- SPÉCIFICATION DU PACKAGE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PACKAGE pkg_datamart AS
  -- Constantes
  c_seuil_fraude_alerte CONSTANT NUMBER := 0.05;  -- 5 % de fraudes

  -- Refresh des vues matérialisées
  PROCEDURE pr_refresh_card_aggregates;
  PROCEDURE pr_refresh_daily_aggregates;
  PROCEDURE pr_refresh_mcc_aggregates;
  PROCEDURE pr_refresh_all_datamarts;

  -- Chargement de la dimension MARCHAND depuis les transactions
  PROCEDURE pr_charger_marchands (p_nb_inserees OUT NUMBER);

  -- Fonctions de calcul d'indicateurs
  FUNCTION fn_calc_taux_fraude_carte   (p_id_carte NUMBER) RETURN NUMBER;
  FUNCTION fn_calc_score_risque_client (p_id_client NUMBER) RETURN NUMBER;
  FUNCTION fn_get_libelle_mcc           (p_code_mcc NUMBER) RETURN VARCHAR2;

  -- Utilitaire d'alerte
  FUNCTION fn_carte_a_risque (p_id_carte NUMBER) RETURN CHAR;
END pkg_datamart;
/

-- -----------------------------------------------------------------------------
-- CORPS DU PACKAGE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE PACKAGE BODY pkg_datamart AS

  -- ---------------------------------------------------------------------------
  -- pr_refresh_card_aggregates
  -- ---------------------------------------------------------------------------
  PROCEDURE pr_refresh_card_aggregates AS
  BEGIN
    DBMS_OUTPUT.PUT_LINE('Refresh mv_card_aggregates...');
    DBMS_MVIEW.REFRESH(
      list           => 'MV_CARD_AGGREGATES',
      method         => 'C',  -- COMPLETE
      atomic_refresh => FALSE
    );
    DBMS_OUTPUT.PUT_LINE('  -> OK');
  EXCEPTION
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Erreur refresh card_aggregates : ' || SQLERRM);
      RAISE;
  END pr_refresh_card_aggregates;

  -- ---------------------------------------------------------------------------
  -- pr_refresh_daily_aggregates
  -- ---------------------------------------------------------------------------
  PROCEDURE pr_refresh_daily_aggregates AS
  BEGIN
    DBMS_OUTPUT.PUT_LINE('Refresh mv_daily_aggregates...');
    DBMS_MVIEW.REFRESH(
      list           => 'MV_DAILY_AGGREGATES',
      method         => 'C',
      atomic_refresh => FALSE
    );
    DBMS_OUTPUT.PUT_LINE('  -> OK');
  EXCEPTION
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Erreur refresh daily_aggregates : ' || SQLERRM);
      RAISE;
  END pr_refresh_daily_aggregates;

  -- ---------------------------------------------------------------------------
  -- pr_refresh_mcc_aggregates
  -- ---------------------------------------------------------------------------
  PROCEDURE pr_refresh_mcc_aggregates AS
  BEGIN
    DBMS_OUTPUT.PUT_LINE('Refresh mv_mcc_aggregates...');
    DBMS_MVIEW.REFRESH(
      list           => 'MV_MCC_AGGREGATES',
      method         => 'C',
      atomic_refresh => FALSE
    );
    DBMS_OUTPUT.PUT_LINE('  -> OK');
  EXCEPTION
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Erreur refresh mcc_aggregates : ' || SQLERRM);
      RAISE;
  END pr_refresh_mcc_aggregates;

  -- ---------------------------------------------------------------------------
  -- pr_refresh_all_datamarts : refresh global
  -- ---------------------------------------------------------------------------
  PROCEDURE pr_refresh_all_datamarts AS
  BEGIN
    DBMS_OUTPUT.PUT_LINE('=== Début refresh global des datamarts ===');
    pr_refresh_card_aggregates;
    pr_refresh_daily_aggregates;
    pr_refresh_mcc_aggregates;
    DBMS_OUTPUT.PUT_LINE('=== Fin refresh global ===');
  END pr_refresh_all_datamarts;

  -- ---------------------------------------------------------------------------
  -- pr_charger_marchands
  -- Charge la dimension MARCHAND par déduplication depuis TRANSACTION
  -- ---------------------------------------------------------------------------
PROCEDURE pr_charger_marchands (p_nb_inserees OUT NUMBER) AS
  BEGIN
    -- Stub : le chargement des marchands se fait via src/migration/load_oracle.py
    -- Cette procédure est conservée pour rester compatible avec une éventuelle
    -- ingestion 100% SQL en V2 (via une table de staging).
    p_nb_inserees := 0;
    DBMS_OUTPUT.PUT_LINE('Procédure stub : chargement via Python (cf migration/load_oracle.py)');
  END pr_charger_marchands;
  -- ---------------------------------------------------------------------------
  -- fn_calc_taux_fraude_carte
  -- Retourne le taux de fraude (en %) pour une carte donnée
  -- ---------------------------------------------------------------------------
  FUNCTION fn_calc_taux_fraude_carte (p_id_carte NUMBER) RETURN NUMBER AS
    v_nb_tx       NUMBER := 0;
    v_nb_fraudes  NUMBER := 0;
    v_taux        NUMBER := 0;
  BEGIN
    SELECT
      COUNT(t.id_transaction),
      SUM(CASE WHEN lf.is_fraud = 'Y' THEN 1 ELSE 0 END)
    INTO  v_nb_tx, v_nb_fraudes
    FROM       transaction t
    LEFT JOIN  label_fraude lf ON t.id_transaction = lf.id_transaction
    WHERE      t.id_carte = p_id_carte;

    IF v_nb_tx = 0 THEN
      RETURN 0;
    END IF;

    v_taux := (v_nb_fraudes * 100.0) / v_nb_tx;
    RETURN ROUND(v_taux, 4);
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN 0;
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Erreur fn_calc_taux_fraude_carte : ' || SQLERRM);
      RETURN NULL;
  END fn_calc_taux_fraude_carte;

  -- ---------------------------------------------------------------------------
  -- fn_calc_score_risque_client
  -- Score simple de risque client : combine taux de fraude moyen et dark web
  -- ---------------------------------------------------------------------------
  FUNCTION fn_calc_score_risque_client (p_id_client NUMBER) RETURN NUMBER AS
    v_taux_moyen      NUMBER := 0;
    v_nb_dark_web     NUMBER := 0;
    v_credit_score    NUMBER := 0;
    v_score           NUMBER := 0;
  BEGIN
    -- Taux de fraude moyen sur les cartes du client
    SELECT  AVG(pkg_datamart.fn_calc_taux_fraude_carte(c.id_carte)),
            SUM(CASE WHEN c.card_on_dark_web = 'Y' THEN 1 ELSE 0 END)
    INTO    v_taux_moyen, v_nb_dark_web
    FROM    carte c
    WHERE   c.id_client = p_id_client;

    SELECT cl.credit_score
    INTO   v_credit_score
    FROM   client cl
    WHERE  cl.id_client = p_id_client;

    -- Score de risque sur 100 (formule simple, à raffiner avec le ML)
    -- Plus le score est élevé, plus le client est à risque
    v_score :=
        NVL(v_taux_moyen, 0) * 5
      + NVL(v_nb_dark_web, 0) * 10
      + (850 - NVL(v_credit_score, 850)) / 10;

    RETURN GREATEST(0, LEAST(100, ROUND(v_score, 2)));
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN NULL;
    WHEN OTHERS THEN
      DBMS_OUTPUT.PUT_LINE('Erreur fn_calc_score_risque_client : ' || SQLERRM);
      RETURN NULL;
  END fn_calc_score_risque_client;

  -- ---------------------------------------------------------------------------
  -- fn_get_libelle_mcc
  -- Lookup simple du libellé MCC depuis le code
  -- ---------------------------------------------------------------------------
  FUNCTION fn_get_libelle_mcc (p_code_mcc NUMBER) RETURN VARCHAR2 AS
    v_libelle VARCHAR2(255);
  BEGIN
    SELECT libelle_mcc INTO v_libelle FROM mcc WHERE code_mcc = p_code_mcc;
    RETURN v_libelle;
  EXCEPTION
    WHEN NO_DATA_FOUND THEN RETURN 'MCC inconnu (' || p_code_mcc || ')';
  END fn_get_libelle_mcc;

  -- ---------------------------------------------------------------------------
  -- fn_carte_a_risque
  -- Retourne 'Y' si le taux de fraude de la carte dépasse le seuil d'alerte
  -- ---------------------------------------------------------------------------
  FUNCTION fn_carte_a_risque (p_id_carte NUMBER) RETURN CHAR AS
    v_taux NUMBER;
  BEGIN
    v_taux := fn_calc_taux_fraude_carte(p_id_carte);
    IF v_taux >= (c_seuil_fraude_alerte * 100) THEN
      RETURN 'Y';
    ELSE
      RETURN 'N';
    END IF;
  END fn_carte_a_risque;

END pkg_datamart;
/

-- -----------------------------------------------------------------------------
-- Grants
-- -----------------------------------------------------------------------------
GRANT EXECUTE ON pkg_datamart TO role_admin, role_etl;
-- Lecture seule des fonctions pour les analystes (utilisées dans des SELECT)
GRANT EXECUTE ON pkg_datamart TO role_data_scientist, role_analyst;

PROMPT '07_packages_plsql.sql terminé avec succès. Package pkg_datamart créé.'
