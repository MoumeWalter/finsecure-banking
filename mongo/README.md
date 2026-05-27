# Scripts MongoDB — FinSecure Banking

> Scripts JavaScript exécutables via `mongosh` pour la création d'index, les aggregation pipelines et les démos.

## Sommaire

| Fichier | Rôle | Quand l'exécuter |
|---|---|---|
| [`01_create_indexes.js`](01_create_indexes.js) | Crée les 8 index (B-tree, partial, composite, TTL) | Après la première migration |
| [`02_aggregation_pipelines.js`](02_aggregation_pipelines.js) | Crée les 3 vues équivalentes aux datamarts Oracle | Après la création des index |
| [`03_demos_soutenance.js`](03_demos_soutenance.js) | 6 requêtes prêtes pour la soutenance | À la demande |

## Procédure d'exécution

### 1. Copier les scripts dans le conteneur

```powershell
docker exec -u 0 mongo_db mkdir -p /tmp/mongo
docker cp mongo/. mongo_db:/tmp/mongo/
docker exec mongo_db ls /tmp/mongo/
```

### 2. Lancer les scripts dans l'ordre

```powershell
$MONGO_URI = "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin"

# 1. Index
docker exec mongo_db mongosh $MONGO_URI --file /tmp/mongo/01_create_indexes.js

# 2. Vues d'aggregation
docker exec mongo_db mongosh $MONGO_URI --file /tmp/mongo/02_aggregation_pipelines.js

# 3. Démos (à exécuter plusieurs fois sans souci)
docker exec mongo_db mongosh $MONGO_URI --file /tmp/mongo/03_demos_soutenance.js
```

### 3. Session interactive `mongosh`

Pour faire des requêtes à la volée :

```powershell
docker exec -it mongo_db mongosh "mongodb://admin:ChangeMeMongo2026@localhost:27017/finsecure?authSource=admin"
```

Dans le prompt `finsecure>` :

```javascript
// Compter les documents
db.transactions_enriched.countDocuments()

// Voir un document
db.transactions_enriched.findOne()

// Voir les index
db.transactions_enriched.getIndexes()

// Quitter
exit
```

## Connexion via MongoDB Compass (GUI)

1. Télécharger Compass : https://www.mongodb.com/try/download/compass
2. Installer (~200 Mo)
3. Lancer Compass
4. Coller la chaîne de connexion :
   ```
   mongodb://admin:ChangeMeMongo2026@localhost:27017/?authSource=admin
   ```
5. Cliquer "Connect"

Tu auras une interface graphique pour explorer les documents, les index, les performances. Très utile pour la démo en soutenance.

## Conventions de nommage

- **Collections** : `transactions_enriched`
- **Vues** : préfixe `v_` (ex. `v_card_aggregates`)
- **Index** :
  - `ux_*` : unique
  - `ix_*` : simple
  - `ttl_*` : avec expiration TTL
