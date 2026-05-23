-- =============================================================================
-- 01_grants.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE après création des tables (03_tables.sql)
--
-- Attribution des droits sur les objets aux 5 rôles applicatifs.
-- Principe : least privilege (chaque rôle a le strict minimum).
--
-- ATTENTION : ce script référence des tables et vues qui doivent exister.
-- Il doit être lancé APRÈS 03_tables.sql, 05_views.sql, 06_materialized_views.sql.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- role_admin : tous les droits (équivalent DBA sur le schéma)
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON client             TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON carte              TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON mcc                TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON marchand           TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON transaction        TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON label_fraude       TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON erreur_transaction TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON utilisateur_si     TO role_admin;
GRANT SELECT, INSERT, UPDATE, DELETE ON journal_audit      TO role_admin;

-- -----------------------------------------------------------------------------
-- role_etl : lecture/écriture sur le métier, lecture sur l'audit
-- -----------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON client             TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON carte              TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON mcc                TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON marchand           TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON transaction        TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON label_fraude       TO role_etl;
GRANT SELECT, INSERT, UPDATE, DELETE ON erreur_transaction TO role_etl;
GRANT SELECT                          ON journal_audit     TO role_etl;

-- -----------------------------------------------------------------------------
-- role_data_scientist : lecture sur Silver/Gold + écriture artefacts ML
-- -----------------------------------------------------------------------------
GRANT SELECT ON client             TO role_data_scientist;
GRANT SELECT ON carte              TO role_data_scientist;
GRANT SELECT ON mcc                TO role_data_scientist;
GRANT SELECT ON marchand           TO role_data_scientist;
GRANT SELECT ON transaction        TO role_data_scientist;
GRANT SELECT ON label_fraude       TO role_data_scientist;
GRANT SELECT ON erreur_transaction TO role_data_scientist;

-- -----------------------------------------------------------------------------
-- role_analyst : lecture sur datamarts uniquement (vues matérialisées)
-- -----------------------------------------------------------------------------
-- Les grants sur mv_card_aggregates et mv_daily_aggregates sont dans 06_materialized_views.sql
-- car les objets doivent exister. Ici on prépare les grants sur les vues simples.
-- GRANT SELECT ON v_transactions_enrichies TO role_analyst;
-- GRANT SELECT ON v_clients_avec_cartes    TO role_analyst;
-- GRANT SELECT ON v_marchands_par_volume   TO role_analyst;
-- (cf 05_views.sql qui contient les grants finaux)

-- -----------------------------------------------------------------------------
-- role_audit : lecture uniquement sur les tables d'audit
-- -----------------------------------------------------------------------------
GRANT SELECT ON journal_audit  TO role_audit;
GRANT SELECT ON utilisateur_si TO role_audit;

-- -----------------------------------------------------------------------------
-- Révocations explicites (defense in depth)
-- -----------------------------------------------------------------------------
-- Personne ne doit pouvoir modifier l'audit (sauf admin pour purge légale)
REVOKE INSERT, UPDATE, DELETE ON journal_audit FROM role_etl;
REVOKE INSERT, UPDATE, DELETE ON journal_audit FROM role_data_scientist;
REVOKE INSERT, UPDATE, DELETE ON journal_audit FROM role_audit;

PROMPT '01_grants.sql terminé avec succès. Droits attribués aux 5 rôles.'
