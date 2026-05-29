# Scripts utilitaires

Scripts PowerShell pour gérer la stack docker compose.

| Script | Action | Confirmation requise |
|---|---|---|
| `start-stack.ps1` | Démarre toute la stack (Oracle + MongoDB + Mongo Express) | Non |
| `stop-stack.ps1` | Arrête la stack en préservant les données | Non |
| `reset-stack.ps1` | **DESTRUCTIF** : supprime conteneurs ET volumes | Oui (double) |

## Utilisation

```powershell
# Première utilisation : autoriser l'exécution des scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Démarrer
.\scripts\start-stack.ps1

# Voir l'état
docker compose ps

# Arrêter (données conservées)
.\scripts\stop-stack.ps1

# Reset complet (DESTRUCTIF)
.\scripts\reset-stack.ps1
```

## Différence entre `stop` et `reset`

- **`stop-stack.ps1`** : arrête les processus dans les conteneurs. Les conteneurs et volumes restent. Tu peux redémarrer avec `start-stack.ps1` et retrouver toutes tes données.
- **`reset-stack.ps1`** : supprime les conteneurs **et** les volumes. Tu perds toutes les données. À utiliser uniquement pour repartir de zéro.
