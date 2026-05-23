-- =============================================================================
-- 08_triggers.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Triggers d'audit alimentant automatiquement JOURNAL_AUDIT sur les tables
-- sensibles (CLIENT, CARTE, UTILISATEUR_SI).
--
-- Conformité : ACPR (traçabilité des accès) + RGPD (article 30, registre
-- des traitements + article 32, sécurité).
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Séquence dédiée à l'audit
-- -----------------------------------------------------------------------------
CREATE SEQUENCE seq_journal_audit
  START WITH 1
  INCREMENT BY 1
  CACHE 1000
  NOCYCLE
  NOORDER;

-- -----------------------------------------------------------------------------
-- Fonction utilitaire : récupère l'id_utilisateur courant
-- -----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION fn_get_current_user_id RETURN NUMBER AS
  v_id NUMBER;
BEGIN
  -- Mapping login Oracle vers id_utilisateur applicatif
  SELECT id_utilisateur INTO v_id
  FROM   utilisateur_si
  WHERE  UPPER(login) = USER;
  RETURN v_id;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    -- Utilisateur technique non référencé (init, batch) → utilisateur système 0
    RETURN 0;
  WHEN OTHERS THEN
    RETURN 0;
END fn_get_current_user_id;
/

-- -----------------------------------------------------------------------------
-- TRIGGER : tr_client_audit
-- Trace toutes les modifications sur CLIENT
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tr_client_audit
AFTER INSERT OR UPDATE OR DELETE ON client
FOR EACH ROW
DECLARE
  v_operation     VARCHAR2(10);
  v_id_ligne      NUMBER(12);
  v_avant         CLOB;
  v_apres         CLOB;
BEGIN
  IF INSERTING THEN
    v_operation := 'INSERT';
    v_id_ligne  := :NEW.id_client;
    v_avant     := NULL;
    v_apres     := '{"id_client":' || :NEW.id_client
                || ',"current_age":' || :NEW.current_age
                || ',"credit_score":' || NVL(TO_CHAR(:NEW.credit_score), 'null')
                || '}';
  ELSIF UPDATING THEN
    v_operation := 'UPDATE';
    v_id_ligne  := :NEW.id_client;
    v_avant     := '{"current_age":' || :OLD.current_age
                || ',"credit_score":' || NVL(TO_CHAR(:OLD.credit_score), 'null')
                || '}';
    v_apres     := '{"current_age":' || :NEW.current_age
                || ',"credit_score":' || NVL(TO_CHAR(:NEW.credit_score), 'null')
                || '}';
  ELSIF DELETING THEN
    v_operation := 'DELETE';
    v_id_ligne  := :OLD.id_client;
    v_avant     := '{"id_client":' || :OLD.id_client
                || ',"current_age":' || :OLD.current_age
                || '}';
    v_apres     := NULL;
  END IF;

  INSERT INTO journal_audit (
    id_audit,
    id_utilisateur,
    table_concernee,
    id_ligne_concernee,
    operation,
    valeur_avant,
    valeur_apres,
    date_operation
  ) VALUES (
    seq_journal_audit.NEXTVAL,
    fn_get_current_user_id,
    'CLIENT',
    v_id_ligne,
    v_operation,
    v_avant,
    v_apres,
    SYSTIMESTAMP
  );
END tr_client_audit;
/

-- -----------------------------------------------------------------------------
-- TRIGGER : tr_carte_audit
-- Trace toutes les modifications sur CARTE (PAN/CVV ne sont jamais loggés)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tr_carte_audit
AFTER INSERT OR UPDATE OR DELETE ON carte
FOR EACH ROW
DECLARE
  v_operation     VARCHAR2(10);
  v_id_ligne      NUMBER(12);
  v_avant         CLOB;
  v_apres         CLOB;
BEGIN
  IF INSERTING THEN
    v_operation := 'INSERT';
    v_id_ligne  := :NEW.id_carte;
    v_avant     := NULL;
    -- IMPORTANT : on ne logue JAMAIS card_number_enc ni cvv_enc (PCI-DSS)
    v_apres     := '{"id_carte":' || :NEW.id_carte
                || ',"id_client":' || :NEW.id_client
                || ',"card_brand":"' || :NEW.card_brand || '"'
                || ',"credit_limit":' || NVL(TO_CHAR(:NEW.credit_limit), 'null')
                || '}';
  ELSIF UPDATING THEN
    v_operation := 'UPDATE';
    v_id_ligne  := :NEW.id_carte;
    v_avant     := '{"credit_limit":' || NVL(TO_CHAR(:OLD.credit_limit), 'null')
                || ',"card_on_dark_web":"' || :OLD.card_on_dark_web || '"'
                || '}';
    v_apres     := '{"credit_limit":' || NVL(TO_CHAR(:NEW.credit_limit), 'null')
                || ',"card_on_dark_web":"' || :NEW.card_on_dark_web || '"'
                || '}';
  ELSIF DELETING THEN
    v_operation := 'DELETE';
    v_id_ligne  := :OLD.id_carte;
    v_avant     := '{"id_carte":' || :OLD.id_carte
                || ',"id_client":' || :OLD.id_client
                || '}';
    v_apres     := NULL;
  END IF;

  INSERT INTO journal_audit (
    id_audit, id_utilisateur, table_concernee, id_ligne_concernee,
    operation, valeur_avant, valeur_apres, date_operation
  ) VALUES (
    seq_journal_audit.NEXTVAL,
    fn_get_current_user_id,
    'CARTE',
    v_id_ligne,
    v_operation,
    v_avant,
    v_apres,
    SYSTIMESTAMP
  );
END tr_carte_audit;
/

-- -----------------------------------------------------------------------------
-- TRIGGER : tr_utilisateur_si_audit
-- Trace toutes les modifications sur les comptes applicatifs
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tr_utilisateur_si_audit
AFTER INSERT OR UPDATE OR DELETE ON utilisateur_si
FOR EACH ROW
DECLARE
  v_operation VARCHAR2(10);
  v_id_ligne  NUMBER(12);
  v_avant     CLOB;
  v_apres     CLOB;
BEGIN
  IF INSERTING THEN
    v_operation := 'INSERT';
    v_id_ligne  := :NEW.id_utilisateur;
    v_apres     := '{"login":"' || :NEW.login || '","role":"' || :NEW.role || '"}';
  ELSIF UPDATING THEN
    v_operation := 'UPDATE';
    v_id_ligne  := :NEW.id_utilisateur;
    v_avant     := '{"role":"' || :OLD.role || '","actif":"' || :OLD.actif || '"}';
    v_apres     := '{"role":"' || :NEW.role || '","actif":"' || :NEW.actif || '"}';
  ELSIF DELETING THEN
    v_operation := 'DELETE';
    v_id_ligne  := :OLD.id_utilisateur;
    v_avant     := '{"login":"' || :OLD.login || '"}';
  END IF;

  INSERT INTO journal_audit (
    id_audit, id_utilisateur, table_concernee, id_ligne_concernee,
    operation, valeur_avant, valeur_apres, date_operation
  ) VALUES (
    seq_journal_audit.NEXTVAL,
    fn_get_current_user_id,
    'UTILISATEUR_SI',
    v_id_ligne,
    v_operation,
    v_avant,
    v_apres,
    SYSTIMESTAMP
  );
END tr_utilisateur_si_audit;
/

-- -----------------------------------------------------------------------------
-- TRIGGER : tr_client_modif_date
-- Met à jour automatiquement date_modification sur UPDATE CLIENT
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tr_client_modif_date
BEFORE UPDATE ON client
FOR EACH ROW
BEGIN
  :NEW.date_modification := SYSTIMESTAMP;
END tr_client_modif_date;
/

-- -----------------------------------------------------------------------------
-- TRIGGER : tr_carte_modif_date
-- Idem sur CARTE
-- -----------------------------------------------------------------------------
CREATE OR REPLACE TRIGGER tr_carte_modif_date
BEFORE UPDATE ON carte
FOR EACH ROW
BEGIN
  :NEW.date_modification := SYSTIMESTAMP;
END tr_carte_modif_date;
/

PROMPT '08_triggers.sql terminé avec succès. 5 triggers créés.'
