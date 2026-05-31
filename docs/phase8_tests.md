# Phase 8 — Tests Pytest

> Cette phase ajoute une couverture de tests pour valider le code et l'API.

## Sommaire

1. [Objectif](#1-objectif)
2. [Stratégie de test](#2-stratégie-de-test)
3. [Organisation](#3-organisation)
4. [Tests unitaires](#4-tests-unitaires)
5. [Tests d'intégration](#5-tests-dintégration)
6. [Couverture de code](#6-couverture-de-code)
7. [Décisions et trade-offs](#7-décisions-et-trade-offs)

---

## 1. Objectif

Mettre en place une **stratégie de tests automatisés** qui :

- Détecte les régressions sur les modules critiques (chiffrement, API)
- Documente le comportement attendu du système
- Permet d'évoluer le code en confiance (refactoring sûr)
- Apporte un argument de qualité pour le jury (industrialisation)

**Non-objectif** : atteindre 100% de couverture. La couverture est mesurée comme indicateur, sans seuil bloquant.

---

## 2. Stratégie de test

### Pyramide de tests adoptée

```
        /\
       /  \         Tests d'intégration (~20)
      /    \        - API FastAPI in-process
     /------\       - MongoDB réel
    /        \      - ~5-10 sec
   /          \
  /            \    Tests unitaires (~25)
 /              \   - Pas d'I/O, pas de DB
/________________\  - Code pur (encryption, models, config)
                    - < 1 sec
```

### Choix techniques

| Outil | Rôle |
|---|---|
| `pytest` 8.x | Runner principal |
| `pytest-asyncio` | Tests async (mode auto) |
| `pytest-cov` | Mesure de couverture |
| `httpx.AsyncClient` | Client HTTP de test pour FastAPI |
| `ASGITransport` | Appel in-process de l'app (pas de serveur réseau) |

### Markers pytest

| Marker | Description |
|---|---|
| `@pytest.mark.unit` | Test unitaire (rapide, isolé) |
| `@pytest.mark.integration` | Nécessite MongoDB |
| `@pytest.mark.slow` | Test long (> 1 sec) |

Exécution sélective :

```bash
pytest -m unit              # Tests rapides uniquement
pytest -m integration       # Tests d'intégration
pytest -m "not slow"        # Tout sauf les lents
```

---

## 3. Organisation

```
tests/
├── conftest.py                     # Fixtures (api_client async, mongo_running)
├── unit/
│   ├── test_encryption.py          # AES-256 GCM (15 tests)
│   ├── test_config.py              # Pydantic Settings (6 tests)
│   └── test_models.py              # Schemas API (12 tests)
└── integration/
    ├── test_health.py              # /health, /docs, /openapi.json (5 tests)
    ├── test_transactions.py        # /transactions/* (6 tests)
    ├── test_clients.py             # /clients/{id}/* (6 tests)
    └── test_datamarts.py           # /datamarts/* (10 tests)

pyproject.toml                      # Configuration pytest + coverage
requirements-test.txt               # Deps tests
```

Total : **~60 tests** organisés.

---

## 4. Tests unitaires

### test_encryption.py

15 tests sur le module AES-256-GCM, organisés en 4 classes :

| Classe | Couverture |
|---|---|
| `TestEncryptDecrypt` | Aller-retour simple, UTF-8, chaînes longues, numériques |
| `TestNullHandling` | Gestion de None et chaîne vide |
| `TestSecurity` | Nonces différents pour mêmes plaintexts, refus mauvaise clé, format base64 valide |
| `TestEnvKey` | Variable d'env absente / mal formée / valide |

**Tests "security property"** notables :

```python
def test_meme_plaintext_ciphertexts_differents(self):
    """Le même plaintext chiffré deux fois doit donner deux ciphertexts différents
    (grâce au nonce aléatoire de 12 bytes)."""
```

C'est une vérification que la propriété de **non-déterminisme** d'AES-GCM est respectée. Sans cette propriété, le chiffrement serait vulnérable aux attaques par dictionnaire sur les colonnes répétitives.

### test_models.py

12 tests sur les schemas Pydantic. Le test le plus intéressant reconstruit une transaction depuis un dict tel que MongoDB le renvoie — cela valide que le contrat entre la DB et l'API est respecté.

---

## 5. Tests d'intégration

### Architecture

```
Test → httpx.AsyncClient → ASGI Transport → FastAPI app → Motor → MongoDB
```

Pas de serveur HTTP réel : l'app est appelée **in-process** via ASGI. Avantages :
- Plus rapide qu'un appel HTTP réel
- Pas besoin de gérer le démarrage du serveur dans les tests
- La vraie MongoDB est utilisée (test d'intégration véritable)

### Fixture `api_client`

```python
@pytest_asyncio.fixture
async def api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        async with app.router.lifespan_context(app):
            yield client
```

Le `lifespan_context` déclenche `connect_mongo()` au début et `close_mongo()` à la fin. Reproduit fidèlement le cycle de vie production.

### Tests notables

#### Propriétés métier vérifiées

```python
async def test_fraud_stats_coherent(self, api_client):
    """La somme par genre doit egaler le nombre total de fraudes."""
    stats = (await api_client.get("/api/v1/datamarts/fraud-stats")).json()
    assert sum(stats["par_genre"].values()) == stats["nb_fraudes"]
```

Ces tests détectent les régressions sur les `$facet` MongoDB. Si quelqu'un casse l'aggregation, le test échoue immédiatement.

#### Cohérence cross-endpoints

```python
async def test_summary_coherent_avec_liste(self, api_client):
    """Le compte du summary doit egaler le total de la liste paginée."""
    total_liste = liste["total"]
    total_summary = summary["nb_transactions"]
    assert total_liste == total_summary
```

Vérifie que deux chemins différents pour obtenir le même chiffre donnent le même résultat. Détecte les bugs de jointure ou de filtre.

#### Validation des entrées

```python
async def test_cards_sort_by_invalide_refuse(self, api_client):
    """Un champ de tri non autorise est rejete par la regex."""
    response = await api_client.get("/api/v1/datamarts/cards?sort_by=injection_attempt")
    assert response.status_code == 422
```

Vérifie que la validation Pydantic protège contre les tentatives d'injection.

---

## 6. Couverture de code

### Mesure

```powershell
pytest --cov --cov-report=term-missing
```

### Stratégie : indicateur, pas gate

**Pas de seuil bloquant** (`fail_under` non configuré).

Justification :
- Forcer 80% pousse à tester du code trivial (getters, `__init__.py`)
- L'objectif est la **valeur métier** des tests
- Un test qui détecte un vrai bug vaut mieux que 10 tests qui couvrent du code mort

### Périmètre exclu

```toml
omit = [
    "tests/*",
    "*/__init__.py",
    "src/migration/load_oracle.py",   # script CLI, testé manuellement
    "src/migration/load_mongo.py",    # script CLI, testé manuellement
]
```

Les scripts de migration sont testés "manuellement" en exécutant la migration réelle (5h pour Oracle, validation par count en base). Les tester en automatique demanderait de mocker oracledb/pymongo entièrement, pour un bénéfice limité.

### Couverture attendue

| Module | Couverture cible | Couverture réelle visée |
|---|---|---|
| `src/migration/encryption.py` | Très élevée (cœur sécurité) | > 90% |
| `src/api/config.py` | Moyenne | > 70% |
| `src/api/models.py` | Moyenne | > 80% |
| `src/api/routers/*` | Bonne (testés via integration) | > 70% |
| `src/api/database.py` | Faible (mock difficile) | > 40% |

---

## 7. Décisions et trade-offs

### Pas de mocks pour MongoDB

**Décision** : utiliser une vraie MongoDB pour les tests d'intégration.

**Pour** :
- Tests représentatifs
- Détecte les vrais problèmes de connexion / requête
- Pas de divergence entre comportement test et prod

**Contre** :
- Plus lent
- Nécessite Docker
- Données partagées entre tests

**Atténuation** : les tests ne modifient pas les données (lectures uniquement), pas d'effet de bord.

### Pas de Great Expectations

**Décision** : skip GE pour cette phase.

**Justification** :
- GE est lourd à configurer (datasources, contexts, expectation suites)
- Les **mêmes assertions** peuvent se faire en pytest avec moins de code
- Le code est ainsi plus simple à lire pour le jury

**Exemple** : la vérification "taux de fraude < 1%" est une assertion pytest d'une ligne :

```python
assert 0 <= stats["taux_global_pct"] < 1.0
```

En GE, ce serait une expectation suite JSON + un script de validation. Plus lourd pour le même résultat.

**En V2** : si le projet doit valider des données à grande échelle (pipeline Airflow, multi-sources), GE redevient pertinent.

### Tests d'intégration en local, pas en CI

**Décision** : les tests d'intégration ne tournent pas en CI (GitHub Actions).

**Justification** :
- Démarrer MongoDB + peupler 100k documents en CI est coûteux
- Le bénéfice marginal ne justifie pas la complexité

**Compensation** : la CI exécute uniquement `pytest -m unit`, donc les tests rapides.

### Pas de tests sur Oracle

**Décision** : les tests d'intégration ciblent uniquement MongoDB (cohérence avec l'API qui n'utilise que MongoDB).

**Justification** :
- L'API en Phase 11 n'interroge que MongoDB
- Tester Oracle nécessiterait `oracledb`, image XE, et beaucoup de setup
- Oracle est validé par les EXPLAIN PLAN et le COUNT en Phase 2

---

## Conformité au Bloc 2

Cette phase couvre la compétence **"Industrialiser le développement avec des tests"** :

| Démonstration | Statut |
|---|---|
| Tests unitaires automatisés | OK (15+ tests sur encryption) |
| Tests d'intégration sur l'API | OK (20+ tests sur 7 endpoints) |
| Mesure de couverture | OK (pytest-cov) |
| Markers et exécution sélective | OK (unit / integration) |
| Configuration centralisée | OK (pyproject.toml) |
| Documentation des tests | OK (tests/README.md) |

---

## Évolutions Sprint 2

- **CI/CD GitHub Actions** (Phase 9) : exécuter `pytest -m unit` à chaque push
- **Tests de charge** (Phase 12) : Locust ou k6 sur l'API
- **Tests de mutation** : `mutmut` pour vérifier la qualité des assertions
- **Tests E2E** : appel HTTP réel sur la stack compose complète
