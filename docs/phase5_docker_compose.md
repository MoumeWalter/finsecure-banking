# Phase 5 — Conteneurisation Docker Compose

> Cette phase rend toute la stack reproductible en une seule commande.

## Sommaire

1. [Objectif et benefices](#1-objectif-et-benefices)
2. [Architecture des services](#2-architecture-des-services)
3. [Strategie d'integration des donnees existantes](#3-strategie-dintegration)
4. [Procedure de demarrage](#4-procedure-de-demarrage)
5. [Commandes du quotidien](#5-commandes-du-quotidien)
6. [Difficultes rencontrees et lecons](#6-difficultes-rencontrees)
7. [Strategie multi-fichiers compose](#7-strategie-multi-fichiers)

---

## 1. Objectif et benefices

### Avant la Phase 5

Demarrer la stack necessitait deux commandes `docker run` manuelles, avec des
flags a memoriser :

```bash
docker run -d --name oracle_db -p 1521:1521 -e ORACLE_PWD=... ...
docker run -d --name mongo_db -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin ...
```

Pas reproductible, pas de healthchecks, pas de reseau Docker dedie, pas de GUI.

### Apres la Phase 5

```bash
docker compose up -d
```

Et tout demarre : Oracle (avec ses 13,3 M lignes), MongoDB (avec ses 100k documents),
Mongo Express (GUI web), reseau, healthchecks, dependances.

### Benefices concrets

| Aspect | Avant | Apres |
|---|---|---|
| Demarrage | 2 commandes manuelles | `docker compose up -d` |
| Configuration | Flags `docker run` a memoriser | `docker-compose.yml` versionne |
| Healthchecks | Aucun | Oui, sur chaque service |
| Reseau | Localhost partage | Reseau Docker dedie `finsecure_net` |
| GUI MongoDB | Compass externe | Mongo Express integre (http://localhost:8081) |
| Reproductibilite | Faible | Totale |

---

## 2. Architecture des services

```
+------------------------------------------------------------+
|              RESEAU DOCKER finsecure_net                    |
|                                                             |
|  +------------+  +------------+  +-------------------+      |
|  | oracle_db  |  | mongo_db   |  | mongo_express     |      |
|  | XE 21c     |  | 7.0        |  | 1.0.2             |      |
|  | port 1521  |  | port 27017 |  | port 8081         |      |
|  | port 5500  |  |            |  | (lecture seule)   |      |
|  |            |  |            |  |                   |      |
|  | healthcheck|  | healthcheck|  | depends_on:       |      |
|  |            |  |            |  |   mongo_db healthy|      |
|  +------+-----+  +------+-----+  +-------+-----------+      |
|         |               |                 |                 |
+---------+---------------+-----------------+-----------------+
          |               |                 |
   +------v------+ +------v------+   +------v------+
   |  donnees    | |   volume    |   |  HTTP 8081  |
   |   dans      | |  externe    |   |  (host)     |
   |   l'image   | | mongo_data  |   |             |
   +-------------+ +-------------+   +-------------+
```

### Services exposes au host

| Service | Port host | URL/Usage |
|---|---|---|
| Oracle Listener | 1521 | Connexion SQL*Plus, oracledb, JDBC |
| Oracle EM Express | 5500 | https://localhost:5500/em (admin web Oracle) |
| MongoDB | 27017 | Connexion mongosh, pymongo, Compass |
| Mongo Express | 8081 | http://localhost:8081 (GUI MongoDB) |

### Healthchecks

- **Oracle** : execute `SELECT 1 FROM dual` toutes les 30s, apres 3 min de demarrage initial.
- **MongoDB** : execute `db.runCommand({ping:1})` toutes les 10s.
- **Mongo Express** : demarre uniquement quand MongoDB est `healthy` (via `depends_on`).

---

## 3. Strategie d'integration des donnees existantes

### Le probleme rencontre

Lors de la conteneurisation, nous avions deja migre 13,3 M de transactions
sur Oracle XE (5h de migration) et 100k documents MongoDB. Il fallait integrer
ces donnees dans le compose **sans les reperdre**.

Premiere tentative : copier les datafiles Oracle vers un volume nomme. Echec :

- Oracle XE stockait les datafiles principaux dans `/opt/oracle/oradata` (copies OK)
- Mais nos tablespaces custom `ts_finsecure_data`, `ts_finsecure_idx`, `ts_finsecure_audit`
  avaient leurs datafiles dans `/opt/oracle/homes/OraDBHome21cXE/dbs/` (hors oradata)
- Au demarrage, Oracle ne trouvait pas ces 3 tablespaces : `ORA-01157`

Cause racine : dans le script `00_init_for_official_xe.sql`, on avait declare :
```sql
CREATE TABLESPACE ts_finsecure_data DATAFILE 'finsecure_data_01.dbf' SIZE 500M ...
```

**Sans chemin absolu**, Oracle place ces fichiers dans `$ORACLE_HOME/dbs/` par defaut,
hors du dossier oradata persistant.

### La solution adoptee : container as artifact

Plutot que de copier des datafiles fragiles et corriger les chemins, nous avons
adopte le pattern **container as artifact** : le conteneur Oracle est commit
en une image autonome qui contient toutes les donnees.

```powershell
docker commit oracle_db finsecure/oracle-backup:latest
```

L'image fait 33 Go. Le compose utilise cette image directement :

```yaml
oracle_db:
  image: finsecure/oracle-backup:latest
  # Pas de volume sur oradata : les donnees sont dans l'image
```

### Avantages

- **Robustesse** : aucun probleme de chemin de datafiles
- **Simplicite** : pas de manipulation de fichiers Oracle delicats
- **Reproductibilite** : `docker compose up -d` restitue exactement le meme etat
- **Portabilite** : l'image peut etre exportee (`docker save`) et importee ailleurs

### Limitations acceptees

- Les **nouvelles** ecritures apres le commit ne sont pas persistantes : un
  `docker compose down` + `up` recree le conteneur depuis l'image, perdant les
  ecritures recentes. Acceptable pour notre cas d'usage (base statique de demonstration).
- L'image fait 33 Go, ne peut pas etre pushee sur GitHub.

### Pour reconstruire l'image depuis zero

Si l'image `finsecure/oracle-backup:latest` n'existe pas sur la machine cible,
la reconstruction passe par la migration complete (cf README) :

1. Lancer Oracle XE officiel via `docker run`
2. Executer les scripts SQL (00 -> 09)
3. Migrer les donnees via `src/migration/load_oracle.py`
4. Commit : `docker commit oracle_db finsecure/oracle-backup:latest`
5. Lancer `docker compose up -d`

### Pour MongoDB : volume nomme classique

MongoDB n'a pas eu ce probleme : ses donnees sont dans `/data/db` (chemin
standard couvert par le volume nomme `finsecure_mongo_data`).

```yaml
mongo_db:
  image: mongo:7.0
  volumes:
    - finsecure_mongo_data:/data/db   # volume nomme persistant
```

---

## 4. Procedure de demarrage

### Premiere fois (image backup deja generee)

```powershell
.\scripts\start-stack.ps1
```

Ou directement :

```powershell
docker compose up -d
```

### Verification

```powershell
docker compose ps
```

Attendu (apres ~3 min pour Oracle) :

```
NAME            STATUS                    PORTS
oracle_db       Up X minutes (healthy)    0.0.0.0:1521->1521/tcp, 5500->5500/tcp
mongo_db        Up X minutes (healthy)    0.0.0.0:27017->27017/tcp
mongo_express   Up X minutes              0.0.0.0:8081->8081/tcp
```

### Validation des donnees

```powershell
# Oracle : doit retourner 13 305 915
docker exec oracle_db bash -c "echo 'SELECT COUNT(*) FROM transaction;' | sqlplus -s finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1"

# MongoDB : doit retourner 100 000
docker exec mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin" --quiet --eval "db.transactions_enriched.countDocuments()"
```

### Acceder a Mongo Express

http://localhost:8081 — login `admin` / `${MONGO_EXPRESS_PASSWORD}` du `.env`.

---

## 5. Commandes du quotidien

| Action | Commande |
|---|---|
| Demarrer la stack | `.\scripts\start-stack.ps1` ou `docker compose up -d` |
| Voir l'etat | `docker compose ps` |
| Voir les logs | `docker compose logs -f <service>` |
| Arreter | `.\scripts\stop-stack.ps1` ou `docker compose stop` |
| Redemarrer un service | `docker compose restart <service>` |
| Console SQL Oracle | `docker exec -it oracle_db sqlplus finsecure/ChangeMeFinSecure2026@//localhost:1521/XEPDB1` |
| Console mongosh | `docker exec -it mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin"` |

---

## 6. Difficultes rencontrees

### 6.1 Le conteneur Oracle sans volume declare

**Constat** : l'inspection du conteneur initial montrait `Mounts: []`. Les
donnees etaient dans la couche du conteneur, pas dans un volume.

**Risque** : un `docker rm oracle_db` aurait detruit les 13,3 M de transactions.

**Solution** : commit du conteneur en image AVANT toute manipulation (`docker commit`).
Cela cree un filet de securite irreversible.

### 6.2 Les datafiles repartis sur 2 emplacements

**Probleme** : les tablespaces custom (cree par le script d'init) avaient leurs
datafiles dans `$ORACLE_HOME/dbs/`, hors du dossier `oradata` que nous
voulions persister.

**Solution adoptee** : pattern container-as-artifact via `docker commit`.
L'image contient l'integralite de l'arborescence Oracle, pas seulement oradata.

**Lecon pour le futur** : dans les scripts DDL, toujours specifier un chemin
absolu pour les datafiles. Exemple :
```sql
CREATE TABLESPACE ts_finsecure_data
  DATAFILE '/opt/oracle/oradata/XE/finsecure_data_01.dbf' SIZE 500M ...
```

### 6.3 Conflit de noms de conteneur

Quand on lance `docker compose up` apres avoir cree des conteneurs avec
`docker run` du meme nom, compose refuse. Solution : `docker rm <nom>` avant.

### 6.4 Le hostname avec underscore

L'image Oracle XE refuse les hostnames contenant `_` (warning bloquant).
Solution dans compose : `hostname: oracledb` (sans underscore), independant du `container_name`.

---

## 7. Strategie multi-fichiers compose

Pour eviter un mega-fichier `docker-compose.yml` ingerable, on adopte une
architecture modulaire :

| Fichier | Phase | Services |
|---|---|---|
| `docker-compose.yml` | Phase 5 | Oracle, MongoDB, Mongo Express |
| `docker-compose.kafka.yml` | Phase 6 | Kafka, Zookeeper, Kafka UI |
| `docker-compose.airflow.yml` | Phase 7 | Airflow webserver, scheduler, worker |
| `docker-compose.api.yml` | Phase 11 | FastAPI |
| `docker-compose.observability.yml` | Phase 12 | Prometheus, Grafana |

### Demarrer plusieurs fichiers ensemble

```powershell
docker compose up -d                                     # Base seulement
docker compose -f docker-compose.yml `
               -f docker-compose.kafka.yml up -d         # + Kafka
```

L'avantage : on demarre **uniquement ce dont on a besoin**.

---

## Conformite au Bloc 2

Cette phase couvre la competence **"Industrialiser le developpement avec conteneurisation"** :

| Demonstration | Statut |
|---|---|
| Conteneurisation multi-services | OK Oracle + MongoDB + Mongo Express |
| Orchestration declarative | OK docker-compose.yml versionne |
| Healthchecks | OK Sur chaque service |
| Reseau dedie | OK finsecure_net |
| Volumes persistants | OK Volume nomme MongoDB |
| Variables d'environnement centralisees | OK .env unique |
| Architecture modulaire | OK Strategie multi-fichiers compose |
| Pattern container-as-artifact | OK Image backup Oracle |
