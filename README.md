# FinSecure Banking — Plateforme data de détection de fraude

> Projet certifiant RNCP36739 — Expert en Ingénierie de Données
> M2 Data Engineering & IA — EFREI Paris Panthéon-Assas
> Auteur : **Walter Moume & Estelle JOLAINE**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Oracle XE](https://img.shields.io/badge/Oracle-XE%2021c-red.svg)](https://www.oracle.com/database/technologies/appdev/xe.html)

## Vue d'ensemble

**FinSecure Banking** est une plateforme data fictive de détection de fraude bancaire, construite pour démontrer les compétences attendues du Bloc 1 du RNCP36739 (Architecture de stockage de données).

### Ce qui est implémenté (Sprint 1)

| Brique | Détail |
|---|---|
| ✅ Modélisation Merise | 9 entités, MCD/MLD/MPD, normalisation 3NF |
| ✅ Oracle XE 21c | 9 tables, 12 index, partitionnement RANGE INTERVAL, PL/SQL |
| ✅ Sécurité | 5 rôles applicatifs + chiffrement AES-256 + audit ACPR/RGPD |
| ✅ Pipeline migration | Python `oracledb`, 22,5 M objets en base validés |
| ✅ Datamarts | 3 vues matérialisées (équivalent SQL des Gold Hive) |

### Ce qui est prévu (Sprint 2)

MongoDB, Docker Compose, Kafka, Airflow, CI/CD, ML, FastAPI, Prometheus/Grafana — voir [`docs/roadmap.md`](docs/roadmap.md).

## Prérequis

| Composant | Version | Vérifier |
|---|---|---|
| Docker Desktop | ≥ 24.0 | `docker --version` |
| Python | 3.11 → 3.14 | `python --version` |
| Git | ≥ 2.40 | `git --version` |
| Espace disque | ≥ 20 Go | Pour Oracle XE + datalake |
| RAM | ≥ 16 Go | Oracle XE consomme ~2 Go |

⚠️ **Compte Oracle Container Registry** : créez un compte gratuit sur https://container-registry.oracle.com et acceptez les termes pour l'image `database/express`.

## Installation pas à pas

### Étape 1 — Cloner le projet

```bash
git clone https://github.com/MoumeWalter/finsecure-banking.git
cd finsecure-banking
```

### Étape 2 — Récupérer le dataset

Source : https://www.kaggle.com/datasets/computingvictor/transactions-fraud-datasets (~400 Mo)

Extraire dans `data/raw/` :
```
data/raw/
├── transactions_data.csv     # ~3.5 Go, 13.3 M lignes
├── users_data.csv            # 2 000 lignes
├── cards_data.csv            # 6 146 lignes
├── mcc_codes.json            # 109 entrées
└── train_fraud_labels.json   # 8.9 M labels
```

### Étape 3 — Lancer Oracle XE dans Docker

```bash
docker login container-registry.oracle.com
docker run -d \
  --name oracle_db \
  -p 1521:1521 \
  -e ORACLE_PWD=password123 \
  -v finsecure_oracle_data:/opt/oracle/oradata \
  container-registry.oracle.com/database/express:latest
```

⏳ Premier démarrage ~3 min. Suivre avec `docker logs -f oracle_db`. Attendre `DATABASE IS READY TO USE!`.

### Étape 4 — Exécuter les scripts SQL

```bash
# Copier les scripts dans le conteneur
docker exec -u 0 oracle_db rm -rf /tmp/sql
docker cp sql/ oracle_db:/tmp/sql/
docker exec -u 0 oracle_db chown -R oracle:oinstall /tmp/sql

# Init (SYS)
docker exec oracle_db bash -c "sqlplus -s sys/password123@//localhost:1521/XEPDB1 as sysdba @/tmp/sql/00_init_for_official_xe.sql"

# Le reste (FINSECURE) - Windows PowerShell :
powershell -ExecutionPolicy Bypass -File .\run_all_sql.ps1

# Le reste (Linux/macOS) :
for script in 02_sequences 03_tables 04_indexes 05_views 06_materialized_views 07_packages_plsql 08_triggers 01_grants; do
    docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/sql/$script.sql"
done
```

### Étape 5 — Bootstrap des comptes

Le trigger d'audit nécessite un compte SYSTEM préexistant :

```bash
docker exec -it oracle_db sqlplus finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1
```

Dans le prompt `SQL>`, taper une à une :
```sql
ALTER TRIGGER tr_utilisateur_si_audit DISABLE;
INSERT INTO utilisateur_si (id_utilisateur, login, nom_complet, role, email)
VALUES (0, 'SYSTEM', 'Compte technique systeme', 'admin', 'system@finsecure.local');
COMMIT;
ALTER TRIGGER tr_utilisateur_si_audit ENABLE;
EXIT;
```

### Étape 6 — Setup Python

```bash
python -m venv .venv

# Activation (Linux/macOS)
source .venv/bin/activate
# Activation (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements-migration.txt
```

⚠️ **Windows** : si erreur "running scripts is disabled" :
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

### Étape 7 — Générer la clé de chiffrement et créer le `.env`

```bash
python -m src.migration.encryption gen_key
# Copier la chaîne base64 retournée
```

Créer `.env` à la racine en copiant `.env.example` :

```ini
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=XEPDB1
ORACLE_USER=finsecure
ORACLE_PASSWORD=ChangeMeFinSecure2026
ENCRYPTION_KEY=<COLLER_LA_CLE>
DATA_DIR=data/raw
BATCH_SIZE=10000
LOG_LEVEL=INFO
```

⚠️ **NE JAMAIS COMMIT le `.env`**. Le `.gitignore` l'exclut déjà — vérifier avec `git status`.

### Étape 8 — Appliquer les patches de migration

Deux patches adaptent les contraintes aux données réelles :

```bash
docker cp sql/99_fix_migration.sql oracle_db:/tmp/sql/
docker exec -u 0 oracle_db chown oracle:oinstall /tmp/sql/99_fix_migration.sql
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/sql/99_fix_migration.sql"

docker cp sql/99_fix_migration_v2.sql oracle_db:/tmp/sql/
docker exec -u 0 oracle_db chown oracle:oinstall /tmp/sql/99_fix_migration_v2.sql
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/sql/99_fix_migration_v2.sql"
```

### Étape 9 — Migration des données

```bash
# Rapide (~10 min)
python -m src.migration.load_oracle --step mcc
python -m src.migration.load_oracle --step clients
python -m src.migration.load_oracle --step cards
python -m src.migration.load_oracle --step marchands

# Long (~5-6 h) — laisser tourner
python -m src.migration.load_oracle --step transactions

# Final (~45 min)
python -m src.migration.load_oracle --step labels
python -m src.migration.load_oracle --step errors
```

⏳ **Durée totale** : ~6 heures. Ne pas mettre la machine en veille.

### Étape 10 — Refresh des datamarts

```bash
docker exec oracle_db bash -c "echo 'SET SERVEROUTPUT ON SIZE 1000000; BEGIN pkg_datamart.pr_refresh_all_datamarts; END; /' | sqlplus finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1"
```

⏳ ~10 minutes.

## Vérification du déploiement

```bash
docker exec oracle_db bash -c "echo \"SELECT 'MCC' AS nom_table, COUNT(*) AS nb FROM mcc UNION ALL SELECT 'CLIENT', COUNT(*) FROM client UNION ALL SELECT 'CARTE', COUNT(*) FROM carte UNION ALL SELECT 'MARCHAND', COUNT(*) FROM marchand UNION ALL SELECT 'TRANSACTION', COUNT(*) FROM transaction UNION ALL SELECT 'LABEL_FRAUDE', COUNT(*) FROM label_fraude UNION ALL SELECT 'ERREUR_TRANSACTION', COUNT(*) FROM erreur_transaction ORDER BY 1;\" | sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1"
```

Résultat attendu :
```
NOM_TABLE              NB
------------------     ----------
CARTE                       6 146
CLIENT                      2 000
ERREUR_TRANSACTION        212 335
LABEL_FRAUDE            8 914 963
MARCHAND                   74 831
MCC                           109
TRANSACTION            13 305 915
```

## Démo en 3 minutes

```bash
# 1. Bilan
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/bilan_migration.sql"

# 2. Chiffrement vivant
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/demo_chiffrement.sql"

# 3. EXPLAIN PLAN (partition pruning)
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/plan1.sql"

# 4. Audit ACPR
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/check_audit.sql"
```

## Documentation

| Document | Contenu |
|---|---|
| [`docs/rapport_technique.md`](docs/rapport_technique.md) | **Rapport principal** |
| [`docs/recap_pedagogique.md`](docs/recap_pedagogique.md) | **Synthèse pour soutenance** |
| [`docs/cadrage_client.md`](docs/cadrage_client.md) | Scénario FinSecure |
| [`docs/veille_technologique.md`](docs/veille_technologique.md) | Justification des choix |
| [`docs/data_model/`](docs/data_model/) | MCD / MLD / MPD + dictionnaire |
| [`docs/phase2_implementation.md`](docs/phase2_implementation.md) | Détail Oracle |
| [`docs/roadmap.md`](docs/roadmap.md) | Plan 13 phases |
| [`sql/README.md`](sql/README.md) | Ordre d'exécution SQL |
| [`src/migration/README.md`](src/migration/README.md) | Procédure migration |

## FAQ et dépannage

### Le téléchargement de l'image Oracle échoue

```bash
docker login container-registry.oracle.com
```
Acceptez les termes sur https://container-registry.oracle.com/ords/f?p=113:4:::NO::::

### Oracle ne démarre pas

```bash
docker logs oracle_db | tail -50
```
Causes : RAM Docker insuffisante (Settings → Resources, allouer ≥ 4 Go), port 1521 pris (utiliser `-p 1522:1521`).

### `ORA-01017: invalid username/password`

- SYS : `sys/password123@//localhost:1521/XEPDB1 as sysdba`
- FINSECURE : `finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1`
- Vérifier `docker ps` que le conteneur tourne.

### `ORA-14039` ou `DPY-3013` pendant la migration

Le code du repo contient déjà les patches pour ces erreurs. Si vous les voyez, re-cloner le repo (vous avez probablement un fichier obsolète).

### Mon `.env` apparaît dans `git status`

```bash
git rm --cached .env
echo ".env" >> .gitignore
git add .gitignore && git commit -m "fix: ignore .env"
```

### Réinitialiser à zéro

```bash
# Soft : vider les tables
docker exec oracle_db bash -c "sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1 @/tmp/sql/99_cleanup.sql"

# Hard : tout effacer (DESTRUCTIF)
docker rm -f oracle_db
docker volume rm finsecure_oracle_data
```

### Monitorer une migration

```bash
# Linux/macOS
watch -n 60 'docker exec oracle_db bash -c "echo \"SELECT COUNT(*) FROM transaction;\" | sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1"'

# Windows PowerShell
while ($true) { docker exec oracle_db bash -c "echo 'SELECT COUNT(*) FROM transaction;' | sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1" ; Start-Sleep -Seconds 60 }
```

### Session SQL interactive

```bash
docker exec -it oracle_db sqlplus finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1
```

## Contribuer

Voir [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Licence

MIT — Voir [`LICENSE`](LICENSE).
