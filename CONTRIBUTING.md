# Guide de contribution

## Workflow Git

Le projet suit un workflow **GitHub Flow** simplifié :

1. La branche `main` est la branche de référence, toujours déployable
2. Toute nouvelle fonctionnalité ou correction passe par une branche dédiée
3. Les branches sont fusionnées dans `main` via Pull Request après revue

## Convention de nommage des branches

```
<type>/<courte-description-en-kebab-case>
```

Types autorisés :
- `feat/` — nouvelle fonctionnalité
- `fix/` — correction de bug
- `docs/` — documentation
- `refactor/` — refactoring sans changement fonctionnel
- `test/` — ajout ou modification de tests
- `chore/` — tâches d'entretien (build, deps, etc.)

Exemples : `feat/oracle-partitioning`, `docs/cadrage-client`, `fix/spark-memory-leak`

## Convention de commits — Conventional Commits

Format : `<type>(<scope>): <description courte en français>`

```
feat(oracle): ajout du partitionnement RANGE sur transactions
fix(api): correction du timeout sur /card_aggregates
docs(architecture): mise à jour du schéma cible avec MongoDB
test(silver): ajout des tests unitaires de clean_money_column
refactor(bronze): extraction du module sqlite_loader
chore(deps): mise à jour de FastAPI à 0.118
```

## Pull Requests

Chaque PR doit contenir :

- Un titre clair suivant la convention de commits
- Une description listant les changements
- Le ou les numéros d'issue liés (si applicable)
- Les éventuels écrans / extraits de logs prouvant le bon fonctionnement
- Une checklist :
  - [ ] Tests passent localement
  - [ ] Lint passe (`black`, `flake8`, `isort`)
  - [ ] Documentation mise à jour si nécessaire

## Style de code

- **Python** : Black + isort + flake8, longueur de ligne 100
- **SQL** : majuscules pour les mots-clés, indentation 2 espaces, alias explicites
- **Markdown** : titres en sentence case, lignes ≤ 120 caractères

## Documentation

Toute nouvelle brique technique doit être documentée dans `docs/`. Si elle implique un choix entre plusieurs technologies, créer ou mettre à jour `docs/veille_technologique.md`.

## Tests

À partir de la Phase 8 (Sprint 2), aucun code n'est mergé sans tests. La couverture cible est de 70 % minimum.
