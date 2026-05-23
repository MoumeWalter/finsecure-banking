-- =============================================================================
-- 00_init_users_tablespaces.sql
-- =============================================================================
-- À exécuter en tant que SYS AS SYSDBA
--
-- Crée les tablespaces dédiés, les utilisateurs/schémas, et les 5 rôles
-- applicatifs définis dans le cadrage client.
-- =============================================================================

ALTER SESSION SET CONTAINER = XEPDB1;

-- -----------------------------------------------------------------------------
-- 1. Tablespaces
-- -----------------------------------------------------------------------------
-- Tablespace principal pour les données métier
CREATE TABLESPACE ts_finsecure_data
  DATAFILE 'finsecure_data_01.dbf'
  SIZE 500M
  AUTOEXTEND ON NEXT 100M MAXSIZE 8G
  EXTENT MANAGEMENT LOCAL
  SEGMENT SPACE MANAGEMENT AUTO;

-- Tablespace dédié aux index (séparation pour performances I/O)
CREATE TABLESPACE ts_finsecure_idx
  DATAFILE 'finsecure_idx_01.dbf'
  SIZE 200M
  AUTOEXTEND ON NEXT 50M MAXSIZE 2G
  EXTENT MANAGEMENT LOCAL
  SEGMENT SPACE MANAGEMENT AUTO;

-- Tablespace dédié à l'audit (cycle de vie séparé, conformité ACPR)
CREATE TABLESPACE ts_finsecure_audit
  DATAFILE 'finsecure_audit_01.dbf'
  SIZE 200M
  AUTOEXTEND ON NEXT 50M MAXSIZE 4G
  EXTENT MANAGEMENT LOCAL
  SEGMENT SPACE MANAGEMENT AUTO;

-- -----------------------------------------------------------------------------
-- 2. Schémas utilisateurs
-- -----------------------------------------------------------------------------
-- Schéma principal métier
CREATE USER finsecure IDENTIFIED BY "ChangeMeFinSecure2026!"
  DEFAULT TABLESPACE ts_finsecure_data
  TEMPORARY TABLESPACE temp
  QUOTA UNLIMITED ON ts_finsecure_data
  QUOTA UNLIMITED ON ts_finsecure_idx;

GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE MATERIALIZED VIEW,
      CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER, CREATE TYPE,
      CREATE SYNONYM, CREATE DATABASE LINK TO finsecure;

-- Schéma audit (isolé)
CREATE USER finsecure_audit IDENTIFIED BY "ChangeMeAudit2026!"
  DEFAULT TABLESPACE ts_finsecure_audit
  TEMPORARY TABLESPACE temp
  QUOTA UNLIMITED ON ts_finsecure_audit;

GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE TRIGGER
  TO finsecure_audit;

-- -----------------------------------------------------------------------------
-- 3. Rôles applicatifs (5 rôles définis dans le cadrage)
-- -----------------------------------------------------------------------------
CREATE ROLE role_admin;
CREATE ROLE role_etl;
CREATE ROLE role_data_scientist;
CREATE ROLE role_analyst;
CREATE ROLE role_audit;

-- Privilèges système (avant grants objets, qui seront en 01_grants.sql)
GRANT CREATE SESSION TO role_admin, role_etl, role_data_scientist, role_analyst, role_audit;

-- -----------------------------------------------------------------------------
-- 4. Comptes techniques par rôle (un par rôle pour démo)
-- -----------------------------------------------------------------------------
CREATE USER usr_admin       IDENTIFIED BY "Admin2026!"        DEFAULT TABLESPACE ts_finsecure_data;
CREATE USER usr_etl         IDENTIFIED BY "Etl2026!"          DEFAULT TABLESPACE ts_finsecure_data;
CREATE USER usr_datascience IDENTIFIED BY "DataScience2026!"  DEFAULT TABLESPACE ts_finsecure_data;
CREATE USER usr_analyst     IDENTIFIED BY "Analyst2026!"      DEFAULT TABLESPACE ts_finsecure_data;
CREATE USER usr_audit       IDENTIFIED BY "Audit2026!"        DEFAULT TABLESPACE ts_finsecure_audit;

GRANT role_admin           TO usr_admin;
GRANT role_etl             TO usr_etl;
GRANT role_data_scientist  TO usr_datascience;
GRANT role_analyst         TO usr_analyst;
GRANT role_audit           TO usr_audit;

PROMPT '00_init_users_tablespaces.sql terminé avec succès.'
