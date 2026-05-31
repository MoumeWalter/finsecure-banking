# Tests — FinSecure Banking

> Tests pytest pour valider le code et l'API.

## Installation

```powershell
pip install -r requirements-test.txt
```

## Exécution

### Tous les tests

```powershell
pytest
```

### Uniquement les tests unitaires (rapides, sans dépendance)

```powershell
pytest -m unit
```

### Uniquement les tests d'intégration (MongoDB doit être démarré)

```powershell
pytest -m integration
```

### Tests d'un fichier précis

```powershell
pytest tests/unit/test_encryption.py
pytest tests/integration/test_datamarts.py -v
```

### Avec couverture

```powershell
# Rapport en console
pytest --cov

# Rapport HTML détaillé (ouvre htmlcov/index.html)
pytest --cov --cov-report=html
```

## Organisation

```
tests/
├── conftest.py              # Fixtures partagees (api_client async, etc.)
├── unit/                    # Tests rapides isoles
│   ├── test_encryption.py   # AES-256 GCM, gestion erreurs
│   ├── test_config.py       # Pydantic Settings
│   └── test_models.py       # Schemas API
└── integration/             # Tests avec vraie MongoDB
    ├── test_health.py
    ├── test_transactions.py
    ├── test_clients.py
    └── test_datamarts.py
```

## Prérequis pour les tests d'intégration

```powershell
docker compose up -d mongo_db
# Et avoir au moins 100k documents dans transactions_enriched
```

## Stratégie de test

### Tests unitaires (~25 tests)

- **Pas de I/O** : pas de réseau, pas de DB, pas de fichier
- Très rapides (< 1 seconde total)
- Testent la logique pure (chiffrement, validation, sérialisation)
- Peuvent tourner en CI sans Docker

### Tests d'intégration (~20 tests)

- Appellent l'API FastAPI en in-process via `httpx.ASGITransport`
- L'API se connecte à MongoDB en vrai
- Vérifient la cohérence des données et le comportement bout-en-bout
- Plus lents (~5-10 sec total) mais bien plus représentatifs

### Property-based tests

Certains tests vérifient des **propriétés métier** plutôt que des valeurs exactes :

```python
# Exemple : la somme par genre doit égaler le total des fraudes
assert sum(stats["par_genre"].values()) == stats["nb_fraudes"]
```

C'est une approche défensive contre la régression : si quelqu'un casse l'aggregation, le test détecte l'incohérence.

## Couverture

La couverture est **mesurée mais pas bloquante** (décision assumée).

Pourquoi pas de seuil ?
- Forcer 80% pousse à tester du code trivial (`__init__.py`, getters)
- On préfère des tests qui détectent de vrais bugs
- L'objectif est la **valeur métier** des tests, pas un pourcentage

Pour voir la couverture actuelle :
```powershell
pytest --cov --cov-report=term-missing
```

Cible raisonnable : 60-70% sur le code métier (encryption, models, routers).
