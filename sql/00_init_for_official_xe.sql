-- Init pour l'image officielle database/express:latest (Oracle XE 21c)
-- À exécuter en tant que SYS AS SYSDBA, connecté sur XEPDB1

CREATE TABLESPACE ts_finsecure_data
  DATAFILE 'finsecure_data_01.dbf' SIZE 500M
  AUTOEXTEND ON NEXT 100M MAXSIZE 8G;

CREATE TABLESPACE ts_finsecure_idx
  DATAFILE 'finsecure_idx_01.dbf' SIZE 200M
  AUTOEXTEND ON NEXT 50M MAXSIZE 2G;

CREATE TABLESPACE ts_finsecure_audit
  DATAFILE 'finsecure_audit_01.dbf' SIZE 200M
  AUTOEXTEND ON NEXT 50M MAXSIZE 4G;

CREATE USER finsecure IDENTIFIED BY "ChangeMeFinSecure2026"
  DEFAULT TABLESPACE ts_finsecure_data
  TEMPORARY TABLESPACE temp
  QUOTA UNLIMITED ON ts_finsecure_data
  QUOTA UNLIMITED ON ts_finsecure_idx
  QUOTA UNLIMITED ON ts_finsecure_audit;

GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE MATERIALIZED VIEW,
      CREATE SEQUENCE, CREATE PROCEDURE, CREATE TRIGGER, CREATE TYPE,
      CREATE SYNONYM TO finsecure;

CREATE ROLE role_admin;
CREATE ROLE role_etl;
CREATE ROLE role_data_scientist;
CREATE ROLE role_analyst;
CREATE ROLE role_audit;

GRANT CREATE SESSION TO role_admin, role_etl, role_data_scientist, role_analyst, role_audit;

EXIT;
