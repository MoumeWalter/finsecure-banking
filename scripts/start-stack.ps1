# =============================================================================
# scripts/start-stack.ps1
# =============================================================================
# Demarre toute la stack docker compose (Oracle + MongoDB + Mongo Express).
#
# Usage :
#   .\scripts\start-stack.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Demarrage de la stack FinSecure" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Aller dans la racine du projet
Set-Location (Split-Path -Parent $PSScriptRoot)

# Verifier qu'on a un .env
if (-Not (Test-Path ".env")) {
    Write-Host "ERREUR : fichier .env manquant a la racine du projet." -ForegroundColor Red
    Write-Host "Copier .env.example vers .env et completer les valeurs." -ForegroundColor Yellow
    exit 1
}

# Verifier que les volumes existent
$volumes = docker volume ls --format "{{.Name}}"
if ($volumes -notcontains "finsecure_oracle_data") {
    Write-Host "ATTENTION : volume finsecure_oracle_data manquant !" -ForegroundColor Yellow
    Write-Host "Si c'est ta premiere installation, le volume sera cree automatiquement." -ForegroundColor Yellow
    Write-Host ""
    $confirm = Read-Host "Continuer (le compose tentera de creer les volumes) ? [O/N]"
    if ($confirm -ne 'O') { exit 1 }
}

# Lancement
Write-Host "Demarrage des services..." -ForegroundColor Green
docker compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ECHEC du demarrage." -ForegroundColor Red
    exit 1
}

# Etat final
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Etat des services" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
docker compose ps

Write-Host ""
Write-Host "Stack demarree. URLs disponibles :" -ForegroundColor Green
Write-Host "  - Oracle (SQL*Plus)     : localhost:1521 / XEPDB1" -ForegroundColor White
Write-Host "  - Oracle EM Express     : https://localhost:5500/em" -ForegroundColor White
Write-Host "  - MongoDB               : localhost:27017" -ForegroundColor White
Write-Host "  - Mongo Express (GUI)   : http://localhost:8081  (login : admin)" -ForegroundColor White
Write-Host ""
Write-Host "Oracle prend ~3 min pour etre healthy. Suivre avec :" -ForegroundColor Yellow
Write-Host "  docker compose logs -f oracle_db" -ForegroundColor White
Write-Host ""
