-- =============================================================================
-- Fix migration v2 : relaxe les contraintes trop strictes
-- =============================================================================

-- 1. Supprimer la contrainte UNIQUE sur libelle_mcc (doublons legitimes dans la source)
ALTER TABLE mcc DROP CONSTRAINT uq_mcc_libelle;

-- 2. Relaxer la contrainte CHECK sur card_type (donnees reelles plus diversifiees)
ALTER TABLE carte DROP CONSTRAINT ck_carte_type;
ALTER TABLE carte ADD CONSTRAINT ck_carte_type CHECK (card_type IS NOT NULL);

-- 3. Idem pour card_brand par precaution
ALTER TABLE carte DROP CONSTRAINT ck_carte_brand;
ALTER TABLE carte ADD CONSTRAINT ck_carte_brand CHECK (card_brand IS NOT NULL);

PROMPT 'Fix v2 applique avec succes';
EXIT;
