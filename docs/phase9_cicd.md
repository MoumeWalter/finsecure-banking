# Phase 9 — CI/CD GitHub Actions

> Cette phase automatise le lint et les tests à chaque push sur GitHub.

## Sommaire

1. [Objectif](#1-objectif)
2. [Stratégie "Light" assumée](#2-stratégie-light-assumée)
3. [Architecture du workflow](#3-architecture-du-workflow)
4. [Comportement attendu](#4-comportement-attendu)
5. [Configuration ruff](#5-configuration-ruff)
6. [Limites connues](#6-limites-connues)

---

## 1. Objectif

Mettre en place une intégration continue (CI) qui :

- Détecte **automatiquement** les régressions à chaque push
- Vérifie la **qualité du code** (lint avec ruff)
- Exécute les **33 tests unitaires** sur un environnement neuf
- Reste **rapide** (< 2 min) pour ne pas freiner le développement

C'est l'argument d'industrialisation attendu par le RNCP36739 Bloc 2.

---

## 2. Stratégie "Light" assumée

Plutôt qu'une CI complexe avec build Docker, matrix Python multi-versions et tests d'intégration, on garde **3 jobs essentiels** :

| Job | Durée | Rôle |
|---|---|---|
| `lint` | ~30 sec | Vérifie le style et les erreurs de code |
| `test-unit` | ~1 min | Exécute pytest -m unit + couverture |

**Pas inclus dans la CI** :

- ❌ Tests d'intégration (nécessitent MongoDB, overkill ici)
- ❌ Build Docker (l'image est buildée localement par les devs)
- ❌ Matrix multi-versions Python (focus sur 3.12 actuelle)
- ❌ Déploiement automatique (pas de prod cible)

**Pourquoi ?**

> "Une CI lente ou flaky est pire qu'aucune CI." 

Si la CI prend 10 min et échoue 30% du temps pour des raisons aléatoires, les développeurs l'ignorent. Mieux vaut une CI courte et fiable qui apporte de la valeur immédiate.

---

## 3. Architecture du workflow

### Fichier `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:  # execution manuelle

jobs:
  lint:        # ruff check
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [...]

  test-unit:   # pytest -m unit + coverage
    needs: lint
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps: [...]
```

### Déclencheurs

- **`push` sur main** : à chaque commit poussé
- **`pull_request`** : sur les PRs ciblant main (avant merge)
- **`workflow_dispatch`** : exécution manuelle depuis l'interface GitHub

### Concurrency control

```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```

Si deux pushes arrivent en quelques secondes, seul le dernier sera exécuté. Économise les minutes GitHub et donne un feedback plus rapide.

### Dépendances entre jobs

`test-unit` dépend de `lint` via `needs: lint`. Si le lint échoue, les tests ne sont pas exécutés (économie de temps).

### Caches

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
    cache: "pip"
    cache-dependency-path: |
      requirements-test.txt
      requirements-api.txt
      requirements-migration.txt
```

Le cache pip accélère les installations de ~30 sec à ~5 sec sur les runs suivants.

### Artefacts

Le job `test-unit` upload deux artefacts :

- `coverage.xml` : rapport de couverture (format Cobertura)
- `junit.xml` : résultats des tests (consommable par Codecov, SonarQube, etc.)

Conservés 30 jours sur GitHub. Téléchargeable depuis l'onglet "Actions" pour analyse.

---

## 4. Comportement attendu

### Sur un push normal

```
✅ lint           ~30 sec  ✓ ruff check OK
✅ test-unit     ~60 sec  ✓ 33 tests passed
                          ✓ Coverage uploaded
Total: ~1m30
```

### Sur un push avec un bug

```
❌ lint           ~30 sec  ✗ E501 line too long
⏸ test-unit              skipped (lint failed)
```

L'auteur reçoit un email + voit la croix rouge à côté du commit sur GitHub.

### Onglet Actions

Sur GitHub, l'onglet **Actions** affiche l'historique de tous les runs avec :
- Le commit déclencheur
- La branche
- La durée
- L'état (✓ vert / ✗ rouge / 🟡 en cours)

Pour la soutenance, c'est **visuel et impressionnant**.

---

## 5. Configuration ruff

### Pourquoi ruff plutôt que black + isort + flake8 ?

| Critère | ruff ✅ | black + isort + flake8 |
|---|---|---|
| Vitesse | 10-100x plus rapide | Lent |
| Outils | 1 binaire unique | 3 outils différents |
| Configuration | 1 section `pyproject.toml` | 3 fichiers de config |
| Compatibilité | Compatible black | Standard historique |

### Règles activées

```toml
[tool.ruff.lint]
select = ["E", "W", "F", "I", "B"]
ignore = [
    "E501",  # line too long
    "B008",  # FastAPI Depends() incompatible
]
```

| Code | Famille | Description |
|---|---|---|
| `E`/`W` | pycodestyle | PEP 8 |
| `F` | pyflakes | Imports inutilisés, variables non définies |
| `I` | isort | Ordre des imports |
| `B` | bugbear | Bugs courants Python |

### Règles désactivées par fichier

```toml
[tool.ruff.lint.per-file-ignores]
"tests/*" = ["F401", "F811", "B017"]
"src/migration/load_oracle.py" = ["F821"]
"src/migration/load_mongo.py" = ["B905"]
```

Les scripts de migration `load_oracle.py` et `load_mongo.py` ont du **code legacy fonctionnel** : on tolère les warnings pour ne pas refactorer sans raison. Les tests utilisent `pytest.raises(Exception)` (B017) qui est intentionnel.

**Justification** : on traite ruff comme une **garde-fou pragmatique**, pas comme un dogme. Refactorer 200 lignes pour zéro bénéfice métier est contre-productif.

---

## 6. Limites connues

### Pas de tests d'intégration en CI

Les 29 tests d'intégration utilisent une vraie MongoDB. Pour les exécuter en CI il faudrait :
- Démarrer un service MongoDB dans le runner
- Peupler avec un échantillon de données (~100 docs)
- Exécuter les tests
- Nettoyer

C'est faisable (GitHub Actions supporte des `services` Docker) mais ajouterait ~2 min au pipeline et de la complexité.

**Décision** : les tests d'intégration tournent en local avant chaque push. La CI valide le lint et les tests unitaires.

### Pas de déploiement

Le projet est en **mode développement**. Il n'y a pas d'environnement de production cible, donc pas de déploiement automatique.

Une vraie pipeline CI/CD complète aurait :
- Build de l'image Docker
- Push vers un registry (Docker Hub, GHCR)
- Déploiement sur un cluster Kubernetes
- Tests fumigatoires post-déploiement
- Rollback automatique en cas d'échec

À ajouter en Sprint 2 si nécessaire.

### Pas de scan de sécurité

Pas de CodeQL, pas de Dependabot, pas de Trivy scan d'image Docker. À ajouter pour un vrai contexte bancaire (audit ANSSI, ACPR).

---

## Conformité au Bloc 2

Cette phase couvre la compétence **"Industrialiser le développement avec une CI/CD"** :

| Démonstration | Statut |
|---|---|
| Workflow CI automatique | ✅ `.github/workflows/ci.yml` |
| Lint automatique | ✅ ruff |
| Tests automatisés | ✅ pytest -m unit |
| Couverture mesurée et archivée | ✅ artefact coverage.xml |
| Concurrence gérée | ✅ cancel-in-progress |
| Cache des dépendances | ✅ pip cache |
| Exécution sur PR | ✅ pull_request trigger |

---

## Évolutions Sprint 2

- **Phase 9.2** : ajouter le build Docker + push vers GHCR (GitHub Container Registry)
- **Phase 9.3** : ajouter Dependabot pour les updates de dépendances
- **Phase 9.4** : ajouter CodeQL pour le scan de sécurité statique
- **Phase 9.5** : ajouter un job déploiement vers un cluster K8s de test
