# Données du projet

> Les fichiers de données ne sont **pas versionnés** dans Git (volumétrie + RGPD).
> Ce README explique comment récupérer et organiser le dataset localement.

## Source du dataset

Le projet utilise un dataset bancaire synthétique disponible publiquement (par exemple sur Kaggle : "IBM Transactions for Anti Money Laundering" ou équivalent). Le dataset n'est **pas** des données réelles de clients.

## Structure attendue après récupération

```
data/
├── README.md                    # Ce fichier
├── raw/                         # Données brutes (à placer ici manuellement)
│   ├── transactions_data.csv
│   ├── users_data.csv
│   ├── cards_data.csv
│   ├── mcc_codes.json
│   └── train_fraud_labels.json
├── legacy/
│   └── legacy_db.sqlite         # Généré par sqlite.ipynb
├── bronze/                      # Généré par feeder.ipynb (Parquet partitionné)
├── silver/                      # Généré par preprocessing.ipynb
└── gold/                        # Généré par datamart.ipynb
    ├── card_aggregates.csv
    └── daily_aggregates.csv
```

## Volumétries

| Fichier | Lignes | Taille approximative |
|---|---|---|
| `transactions_data.csv` | 22 M | ~ 3,5 Go |
| `users_data.csv` | 2 000 | ~ 350 Ko |
| `cards_data.csv` | 6 146 | ~ 750 Ko |
| `mcc_codes.json` | 109 | ~ 5 Ko |
| `train_fraud_labels.json` | 8,9 M | ~ 200 Mo |

**Espace disque total recommandé** : 20 Go (incluant les couches Bronze/Silver/Gold après ingestion).

## Procédure d'installation

1. Télécharger le dataset depuis sa source
2. Placer tous les fichiers dans `data/raw/`
3. Lancer le notebook `notebooks/00_sqlite_legacy.ipynb` pour générer la BDD legacy
4. Lancer la chaîne `notebooks/01_bronze.ipynb` → `02_silver.ipynb` → `03_gold.ipynb`

## RGPD et anonymisation

Bien que le dataset soit synthétique, le projet implémente l'ensemble des bonnes pratiques RGPD comme s'il s'agissait de vraies données :

- Chiffrement at-rest des colonnes sensibles (numéro de carte, CVV, revenus)
- Durée de conservation paramétrable (TTL MongoDB, archivage Oracle)
- Droit à l'oubli implémenté côté API (`DELETE /clients/{id}`)
- Pseudonymisation des `client_id` côté datalake analytique

Voir `docs/securite_rgpd.md` (à venir Sprint 2) pour le détail.
