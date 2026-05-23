-- =============================================================================
-- 03_tables.sql
-- =============================================================================
-- À exécuter en tant que FINSECURE
--
-- Création des 9 tables du modèle physique, avec :
--   - Clés primaires
--   - Clés étrangères avec ON DELETE adapté
--   - Contraintes CHECK pour la cohérence métier
--   - Contraintes NOT NULL
--   - Partitionnement RANGE INTERVAL sur TRANSACTION
-- =============================================================================

-- Ordre de création respectant les dépendances de clés étrangères :
-- 1. Tables sans dépendance       : MCC, UTILISATEUR_SI
-- 2. Tables avec une dépendance  : CLIENT, MARCHAND, JOURNAL_AUDIT
-- 3. Tables avec deux dépendances : CARTE, TRANSACTION
-- 4. Tables enfants de TRANSACTION : LABEL_FRAUDE, ERREUR_TRANSACTION

-- -----------------------------------------------------------------------------
-- 1. MCC : référentiel des catégories de marchands
-- -----------------------------------------------------------------------------
CREATE TABLE mcc (
  code_mcc      NUMBER(4)      NOT NULL,
  libelle_mcc   VARCHAR2(255)  NOT NULL,
  CONSTRAINT pk_mcc PRIMARY KEY (code_mcc),
  CONSTRAINT uq_mcc_libelle UNIQUE (libelle_mcc),
  CONSTRAINT ck_mcc_code CHECK (code_mcc BETWEEN 0 AND 9999)
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE  mcc IS 'Référentiel ISO 18245 des catégories de marchands';
COMMENT ON COLUMN mcc.code_mcc    IS 'Code MCC à 4 chiffres';
COMMENT ON COLUMN mcc.libelle_mcc IS 'Libellé textuel de la catégorie';

-- -----------------------------------------------------------------------------
-- 2. UTILISATEUR_SI : utilisateurs applicatifs (audit)
-- -----------------------------------------------------------------------------
CREATE TABLE utilisateur_si (
  id_utilisateur            NUMBER(8)      NOT NULL,
  login                     VARCHAR2(50)   NOT NULL,
  nom_complet               VARCHAR2(150)  NOT NULL,
  role                      VARCHAR2(30)   NOT NULL,
  email                     VARCHAR2(150)  NOT NULL,
  actif                     CHAR(1)        DEFAULT 'Y' NOT NULL,
  date_creation             TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  date_derniere_connexion   TIMESTAMP(0),
  CONSTRAINT pk_utilisateur_si        PRIMARY KEY (id_utilisateur),
  CONSTRAINT uq_utilisateur_login     UNIQUE (login),
  CONSTRAINT uq_utilisateur_email     UNIQUE (email),
  CONSTRAINT ck_utilisateur_role      CHECK (role IN ('admin','etl','data_scientist','analyst','audit')),
  CONSTRAINT ck_utilisateur_actif     CHECK (actif IN ('Y','N'))
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE utilisateur_si IS 'Utilisateurs applicatifs du SI pour audit RGPD/ACPR';

-- -----------------------------------------------------------------------------
-- 3. CLIENT : référentiel des titulaires
-- -----------------------------------------------------------------------------
CREATE TABLE client (
  id_client           NUMBER(10)     NOT NULL,
  current_age         NUMBER(3)      NOT NULL,
  retirement_age      NUMBER(3),
  birth_year          NUMBER(4)      NOT NULL,
  birth_month         NUMBER(2),
  gender              VARCHAR2(10),
  address             VARCHAR2(255),
  latitude            NUMBER(8,5),
  longitude           NUMBER(9,5),
  per_capita_income   NUMBER(12,2),
  yearly_income       NUMBER(12,2),
  total_debt          NUMBER(12,2),
  credit_score        NUMBER(4),
  num_credit_cards    NUMBER(3)      NOT NULL,
  date_creation       TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  date_modification   TIMESTAMP(0),
  CONSTRAINT pk_client                PRIMARY KEY (id_client),
  CONSTRAINT ck_client_current_age    CHECK (current_age > 0 AND current_age < 130),
  CONSTRAINT ck_client_retirement_age CHECK (retirement_age IS NULL OR (retirement_age > 0 AND retirement_age < 130)),
  CONSTRAINT ck_client_birth_year     CHECK (birth_year >= 1900),
  CONSTRAINT ck_client_birth_month    CHECK (birth_month IS NULL OR birth_month BETWEEN 1 AND 12),
  CONSTRAINT ck_client_gender         CHECK (gender IS NULL OR gender IN ('Male','Female','Other')),
  CONSTRAINT ck_client_latitude       CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  CONSTRAINT ck_client_longitude      CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
  CONSTRAINT ck_client_credit_score   CHECK (credit_score IS NULL OR credit_score BETWEEN 300 AND 850),
  CONSTRAINT ck_client_num_cards      CHECK (num_credit_cards >= 0),
  CONSTRAINT ck_client_income_pos     CHECK (yearly_income IS NULL OR yearly_income >= 0),
  CONSTRAINT ck_client_debt_pos       CHECK (total_debt IS NULL OR total_debt >= 0)
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE  client IS 'Référentiel KYC des clients. Données sensibles chiffrées côté application.';
COMMENT ON COLUMN client.address       IS 'Adresse postale chiffrée AES-256 (RGPD)';
COMMENT ON COLUMN client.yearly_income IS 'Revenu annuel chiffré AES-256 (RGPD)';
COMMENT ON COLUMN client.total_debt    IS 'Dette totale chiffrée AES-256 (RGPD)';

-- -----------------------------------------------------------------------------
-- 4. MARCHAND : dimension dérivée par DISTINCT
-- -----------------------------------------------------------------------------
CREATE TABLE marchand (
  id_marchand     NUMBER(10)     NOT NULL,
  code_mcc        NUMBER(4)      NOT NULL,
  merchant_city   VARCHAR2(100),
  merchant_state  VARCHAR2(50),
  zip             VARCHAR2(10),
  date_creation   TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT pk_marchand     PRIMARY KEY (id_marchand),
  CONSTRAINT fk_marchand_mcc FOREIGN KEY (code_mcc) REFERENCES mcc(code_mcc)
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE marchand IS 'Dimension MARCHAND dérivée des transactions par SELECT DISTINCT à l''ingestion';

-- -----------------------------------------------------------------------------
-- 5. CARTE : cartes bancaires
-- -----------------------------------------------------------------------------
CREATE TABLE carte (
  id_carte                NUMBER(10)     NOT NULL,
  id_client               NUMBER(10)     NOT NULL,
  card_brand              VARCHAR2(20)   NOT NULL,
  card_type               VARCHAR2(20)   NOT NULL,
  card_number_enc         VARCHAR2(255)  NOT NULL,
  expires                 VARCHAR2(7)    NOT NULL,
  cvv_enc                 VARCHAR2(255)  NOT NULL,
  has_chip                CHAR(1)        NOT NULL,
  num_cards_issued        NUMBER(3),
  credit_limit            NUMBER(12,2),
  acct_open_date          DATE           NOT NULL,
  year_pin_last_changed   NUMBER(4),
  card_on_dark_web        CHAR(1)        NOT NULL,
  date_creation           TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  date_modification       TIMESTAMP(0),
  CONSTRAINT pk_carte              PRIMARY KEY (id_carte),
  CONSTRAINT fk_carte_client       FOREIGN KEY (id_client) REFERENCES client(id_client),
  CONSTRAINT ck_carte_brand        CHECK (card_brand IN ('Visa','Mastercard','Amex','Discover')),
  CONSTRAINT ck_carte_type         CHECK (card_type IN ('Credit','Debit','Debit Prepaid')),
  CONSTRAINT ck_carte_has_chip     CHECK (has_chip IN ('Y','N')),
  CONSTRAINT ck_carte_dark_web     CHECK (card_on_dark_web IN ('Y','N')),
  CONSTRAINT ck_carte_credit_lim   CHECK (credit_limit IS NULL OR credit_limit >= 0),
  CONSTRAINT ck_carte_num_issued   CHECK (num_cards_issued IS NULL OR num_cards_issued >= 0),
  CONSTRAINT ck_carte_pin_year     CHECK (year_pin_last_changed IS NULL OR year_pin_last_changed >= 1900)
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE  carte IS 'Cartes bancaires émises. PAN et CVV chiffrés AES-256.';
COMMENT ON COLUMN carte.card_number_enc IS 'PAN chiffré AES-256 (PCI-DSS / RGPD)';
COMMENT ON COLUMN carte.cvv_enc         IS 'CVV chiffré AES-256 (PCI-DSS / RGPD)';

-- -----------------------------------------------------------------------------
-- 6. TRANSACTION : table de faits, PARTITIONNÉE par mois
-- -----------------------------------------------------------------------------
CREATE TABLE transaction (
  id_transaction    NUMBER(12)     NOT NULL,
  id_carte          NUMBER(10)     NOT NULL,
  id_marchand       NUMBER(10)     NOT NULL,
  date_transaction  TIMESTAMP(0)   NOT NULL,
  amount            NUMBER(12,2)   NOT NULL,
  use_chip          VARCHAR2(30),
  situation_date    DATE           NOT NULL,
  date_creation     TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT pk_transaction          PRIMARY KEY (id_transaction),
  CONSTRAINT fk_transaction_carte    FOREIGN KEY (id_carte)    REFERENCES carte(id_carte),
  CONSTRAINT fk_transaction_marchand FOREIGN KEY (id_marchand) REFERENCES marchand(id_marchand),
  CONSTRAINT ck_transaction_use_chip CHECK (use_chip IS NULL OR use_chip IN
    ('Swipe Transaction','Chip Transaction','Online Transaction'))
) TABLESPACE ts_finsecure_data
PARTITION BY RANGE (situation_date)
INTERVAL (NUMTOYMINTERVAL(1, 'MONTH'))
(
  PARTITION p_initial VALUES LESS THAN (TO_DATE('2024-01-01', 'YYYY-MM-DD'))
);

COMMENT ON TABLE  transaction IS 'Table de faits des transactions. Partitionnée par RANGE INTERVAL mensuel sur situation_date.';
COMMENT ON COLUMN transaction.situation_date IS 'Date d''ingestion utilisée comme clé de partitionnement physique';

-- -----------------------------------------------------------------------------
-- 7. LABEL_FRAUDE : labels ML (cardinalité 0,1 côté transaction)
-- -----------------------------------------------------------------------------
CREATE TABLE label_fraude (
  id_transaction  NUMBER(12)     NOT NULL,
  is_fraud        CHAR(1)        NOT NULL,
  date_creation   TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT pk_label_fraude       PRIMARY KEY (id_transaction),
  CONSTRAINT fk_label_transaction  FOREIGN KEY (id_transaction)
    REFERENCES transaction(id_transaction) ON DELETE CASCADE,
  CONSTRAINT ck_label_is_fraud     CHECK (is_fraud IN ('Y','N'))
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE label_fraude IS 'Labels de fraude pour le ML supervisé. PK identique à FK = relation 0,1.';

-- -----------------------------------------------------------------------------
-- 8. ERREUR_TRANSACTION : éclatement de la colonne multi-valuée errors
-- -----------------------------------------------------------------------------
CREATE TABLE erreur_transaction (
  id_erreur       NUMBER(12)     NOT NULL,
  id_transaction  NUMBER(12)     NOT NULL,
  code_erreur     VARCHAR2(100)  NOT NULL,
  date_creation   TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  CONSTRAINT pk_erreur_transaction      PRIMARY KEY (id_erreur),
  CONSTRAINT fk_erreur_transaction_tx   FOREIGN KEY (id_transaction)
    REFERENCES transaction(id_transaction) ON DELETE CASCADE
) TABLESPACE ts_finsecure_data;

COMMENT ON TABLE erreur_transaction IS 'Erreurs survenues pendant les transactions, issues de l''éclatement de la colonne errors (1NF)';

-- -----------------------------------------------------------------------------
-- 9. JOURNAL_AUDIT : trace ACPR/RGPD
-- -----------------------------------------------------------------------------
-- Note : créée dans le schéma FINSECURE pour simplicité du Sprint 1.
-- En production, serait dans le schéma FINSECURE_AUDIT isolé.
CREATE TABLE journal_audit (
  id_audit              NUMBER(15)     NOT NULL,
  id_utilisateur        NUMBER(8)      NOT NULL,
  table_concernee       VARCHAR2(50)   NOT NULL,
  id_ligne_concernee    NUMBER(12)     NOT NULL,
  operation             VARCHAR2(10)   NOT NULL,
  valeur_avant          CLOB,
  valeur_apres          CLOB,
  date_operation        TIMESTAMP(0)   DEFAULT SYSTIMESTAMP NOT NULL,
  adresse_ip            VARCHAR2(45),
  CONSTRAINT pk_journal_audit       PRIMARY KEY (id_audit),
  CONSTRAINT fk_audit_utilisateur   FOREIGN KEY (id_utilisateur) REFERENCES utilisateur_si(id_utilisateur),
  CONSTRAINT ck_audit_operation     CHECK (operation IN ('INSERT','UPDATE','DELETE'))
) TABLESPACE ts_finsecure_audit;

COMMENT ON TABLE journal_audit IS 'Journal d''audit ACPR/RGPD. Alimenté automatiquement par les triggers.';

PROMPT '03_tables.sql terminé avec succès. 9 tables créées.'
