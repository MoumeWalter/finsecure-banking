# =============================================================================
# scripts/train-model.ps1
# =============================================================================
# Entraine le modele de detection de fraude depuis les donnees MongoDB.
#
# Pre-requis :
#   - Stack docker compose demarree (mongo_db sur localhost:27017)
#   - venv Python active
#   - requirements-ml.txt installe (pip install -r requirements-ml.txt)
#
# Usage :
#   .\scripts\train-model.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Entrainement du modele de fraude" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location (Split-Path -Parent $PSScriptRoot)

# Verifier que MongoDB tourne
$mongoStatus = docker compose ps mongo_db --format json 2>$null
if (-Not $mongoStatus) {
    Write-Host "ERREUR : MongoDB ne tourne pas. Lance d'abord :" -ForegroundColor Red
    Write-Host "  docker compose up -d" -ForegroundColor Yellow
    exit 1
}

# Lancer le training
Write-Host "Lancement du training (peut prendre 2-3 min sur 100k transactions)..." -ForegroundColor Green
Write-Host ""

python -m src.ml.train

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ECHEC du training." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Modele entraine et sauvegarde dans models/" -ForegroundColor Green
Write-Host ""
Write-Host "Contenu de models/ :" -ForegroundColor White
Get-ChildItem models | Format-Table Name, Length, LastWriteTime

Write-Host ""
Write-Host "Prochaines etapes :" -ForegroundColor Cyan
Write-Host "  1. Rebuild l'image API   : docker compose up -d --build finsecure_api" -ForegroundColor White
Write-Host "  2. Tester l'endpoint     : http://localhost:8000/docs#/prediction" -ForegroundColor White
Write-Host ""
