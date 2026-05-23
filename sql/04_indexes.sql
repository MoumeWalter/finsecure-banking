-- =============================================================================
-- 04_indexes.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Création des index selon la stratégie définie en Phase 1 (modele_donnees.md).
-- Tous les index sont créés dans le tablespace TS_FINSECURE_IDX pour séparation
-- physique I/O des données et des index.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- INDEX B-TREE SUR CLÉS ÉTRANGÈRES
-- -----------------------------------------------------------------------------
-- Toute FK doit être indexée pour éviter les locks Oracle sur les jointures
-- et la propagation de DELETE/UPDATE depuis la table parent.

CREATE INDEX ix_carte_id_client
  ON carte(id_client)
  TABLESPACE ts_finsecure_idx;

CREATE INDEX ix_marchand_code_mcc
  ON marchand(code_mcc)
  TABLESPACE ts_finsecure_idx;

-- L'index sur transaction.id_carte est LOCAL car la table est partitionnée
CREATE INDEX ix_transaction_id_carte
  ON transaction(id_carte)
  LOCAL
  TABLESPACE ts_finsecure_idx;

CREATE INDEX ix_transaction_id_marchand
  ON transaction(id_marchand)
  LOCAL
  TABLESPACE ts_finsecure_idx;

CREATE INDEX ix_erreur_id_transaction
  ON erreur_transaction(id_transaction)
  TABLESPACE ts_finsecure_idx;

CREATE INDEX ix_audit_id_utilisateur
  ON journal_audit(id_utilisateur)
  TABLESPACE ts_finsecure_audit;

-- -----------------------------------------------------------------------------
-- INDEX B-TREE POUR FILTRES TEMPORELS
-- -----------------------------------------------------------------------------
-- date_transaction : requêtes datamart filtrent fréquemment sur l'heure/jour

CREATE INDEX ix_transaction_date
  ON transaction(date_transaction)
  LOCAL
  TABLESPACE ts_finsecure_idx;

CREATE INDEX ix_audit_date_operation
  ON journal_audit(date_operation)
  TABLESPACE ts_finsecure_audit;

-- -----------------------------------------------------------------------------
-- INDEX COMPOSITES (requêtes multi-colonnes fréquentes)
-- -----------------------------------------------------------------------------
-- Sert les requêtes du type "transactions d'une carte sur une période"
-- Ordre des colonnes : la plus sélective en premier (id_carte > situation_date)

CREATE INDEX ix_transaction_carte_date
  ON transaction(id_carte, situation_date)
  LOCAL
  TABLESPACE ts_finsecure_idx;

-- Audit ciblé par table modifiée + période
CREATE INDEX ix_audit_table_date
  ON journal_audit(table_concernee, date_operation)
  TABLESPACE ts_finsecure_audit;

-- -----------------------------------------------------------------------------
-- INDEX BITMAP (très faible cardinalité)
-- -----------------------------------------------------------------------------
-- Index bitmap = idéal quand la colonne a peu de valeurs distinctes (ici 2 : Y/N)
-- Très efficace pour les agrégats par catégorie sur grosse table

CREATE BITMAP INDEX bx_label_is_fraud
  ON label_fraude(is_fraud)
  TABLESPACE ts_finsecure_idx;

-- -----------------------------------------------------------------------------
-- INDEX SUR CODE_ERREUR (pour les agrégats par type d'erreur)
-- -----------------------------------------------------------------------------
CREATE INDEX ix_erreur_code
  ON erreur_transaction(code_erreur)
  TABLESPACE ts_finsecure_idx;

-- -----------------------------------------------------------------------------
-- COLLECTE DES STATISTIQUES (essentiel pour l'optimiseur Oracle)
-- -----------------------------------------------------------------------------
-- Sans statistiques fraîches, l'optimiseur fait des choix sous-optimaux.
-- À relancer après chaque grosse ingestion (idéalement via DBMS_SCHEDULER).

BEGIN
  DBMS_STATS.GATHER_SCHEMA_STATS(
    ownname          => 'FINSECURE',
    estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
    cascade          => TRUE
  );
END;
/

PROMPT '04_indexes.sql terminé avec succès. Index + statistiques générés.'
