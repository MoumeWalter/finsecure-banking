-- =============================================================================
-- Fix migration : prepare la base pour le chargement des donnees
-- =============================================================================

-- 1. Vider la table MCC (test manuel a laisse une ligne)
DELETE FROM mcc;
COMMIT;

-- 2. Supprimer les contraintes CHECK incompatibles avec le chiffrement
ALTER TABLE client DROP CONSTRAINT ck_client_income_pos;
ALTER TABLE client DROP CONSTRAINT ck_client_debt_pos;

-- 3. Convertir les colonnes chiffrees de NUMBER vers VARCHAR2
ALTER TABLE client MODIFY (per_capita_income VARCHAR2(255));
ALTER TABLE client MODIFY (yearly_income VARCHAR2(255));
ALTER TABLE client MODIFY (total_debt VARCHAR2(255));

PROMPT 'Fix applique avec succes';
EXIT;
