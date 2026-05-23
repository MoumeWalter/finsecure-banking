# Migration des données vers Oracle XE

## Prérequis

1. Oracle XE 21c installé et accessible (local ou Docker)
2. Scripts SQL 00 à 08 exécutés dans l'ordre (voir [`sql/README.md`](../../sql/README.md))
3. Datasets en place dans `data/raw/` (voir [`data/README.md`](../../data/README.md))
4. Variables d'environnement renseignées dans `.env`
5. Python 3.11 et dépendances installées :

```bash
pip install -r requirements-migration.txt
```

## Générer la clé de chiffrement

À ne faire qu'une fois, puis stocker la clé dans `.env` :

```bash
python -m src.migration.encryption gen_key
# Copier le résultat dans ENCRYPTION_KEY=... du .env
```

## Lancer la migration complète

```bash
python -m src.migration.load_oracle --step all
```

## Lancer une étape isolée

```bash
python -m src.migration.load_oracle --step mcc          # 109 lignes
python -m src.migration.load_oracle --step clients      # 2 000 lignes
python -m src.migration.load_oracle --step cards        # 6 146 lignes
python -m src.migration.load_oracle --step marchands    # ~10 000 lignes
python -m src.migration.load_oracle --step transactions # 22 M lignes (~30 min)
python -m src.migration.load_oracle --step labels       # 8,9 M lignes
python -m src.migration.load_oracle --step errors       # ~20 000 lignes
```

## Ordre obligatoire

Les étapes doivent être exécutées dans l'ordre suivant pour respecter les FK :

```
mcc → clients → cards → marchands → transactions → labels → errors
```

## Après la migration

Refresh des datamarts (vues matérialisées) :

```sql
BEGIN pkg_datamart.pr_refresh_all_datamarts; END;
/
```

## Performance attendue

| Étape | Volumétrie | Temps approximatif (XE local) |
|---|---|---|
| MCC | 109 | < 1 s |
| Clients | 2 000 | ~ 5 s |
| Cartes | 6 146 | ~ 15 s |
| Marchands | ~10 000 | ~ 8 min (lecture des 22 M lignes pour DISTINCT) |
| Transactions | 22 M | ~ 30 min |
| Labels | 8,9 M | ~ 8 min |
| Erreurs | ~20 000 | ~ 10 min (re-scan des 22 M lignes) |
| **Total** | | **~ 60 min** |

## Vérifications post-migration

```sql
-- Cohérence des comptes
SELECT 'CLIENT'   AS t, COUNT(*) FROM client       UNION ALL
SELECT 'CARTE',           COUNT(*) FROM carte         UNION ALL
SELECT 'MARCHAND',        COUNT(*) FROM marchand      UNION ALL
SELECT 'TRANSACTION',     COUNT(*) FROM transaction   UNION ALL
SELECT 'LABEL_FRAUDE',    COUNT(*) FROM label_fraude  UNION ALL
SELECT 'ERREUR_TX',       COUNT(*) FROM erreur_transaction;

-- Intégrité référentielle (doit retourner 0)
SELECT COUNT(*) FROM transaction t
  LEFT JOIN carte c ON t.id_carte = c.id_carte
  WHERE c.id_carte IS NULL;

-- Test du chiffrement (depuis Python)
python -c "from src.migration.encryption import decrypt; \
import oracledb, os; from dotenv import load_dotenv; load_dotenv(); \
conn = oracledb.connect(user=os.environ['ORACLE_USER'], \
  password=os.environ['ORACLE_PASSWORD'], \
  dsn=oracledb.makedsn(os.environ['ORACLE_HOST'], os.environ['ORACLE_PORT'], \
  service_name=os.environ['ORACLE_SERVICE_NAME'])); \
cur = conn.cursor(); cur.execute('SELECT address FROM client WHERE rownum = 1'); \
row = cur.fetchone(); print('Chiffré:', row[0]); print('Déchiffré:', decrypt(row[0]))"
```
