-- =============================================================================
-- 02_sequences.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Séquences pour les identifiants techniques générés en interne.
-- Les identifiants venant directement des sources (id_client, id_carte,
-- id_transaction) n'ont pas de séquence : ils sont insérés tels quels.
-- =============================================================================

-- Séquence pour MARCHAND (table déduite par DISTINCT, pas d'ID source fiable)
CREATE SEQUENCE seq_marchand
  START WITH 1
  INCREMENT BY 1
  CACHE 100
  NOCYCLE
  NOORDER;

-- Séquence pour ERREUR_TRANSACTION (clé technique pour table d'éclatement)
CREATE SEQUENCE seq_erreur_transaction
  START WITH 1
  INCREMENT BY 1
  CACHE 500
  NOCYCLE
  NOORDER;

-- Séquence pour UTILISATEUR_SI
CREATE SEQUENCE seq_utilisateur_si
  START WITH 1
  INCREMENT BY 1
  NOCACHE
  NOCYCLE
  NOORDER;

PROMPT '02_sequences.sql terminé avec succès.'
