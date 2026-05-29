# =============================================================================
# scripts/stop-stack.ps1
# =============================================================================
# Arrete proprement la stack docker compose SANS supprimer les donnees.
# Les conteneurs sont stoppes, les volumes sont conserves.
#
# Usage :
#   .\scripts\stop-stack.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Arret de la stack FinSecure" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Arret des services (les donnees sont conservees)..." -ForegroundColor Yellow
docker compose stop

Write-Host ""
Write-Host "Stack arretee." -ForegroundColor Green
Write-Host "Pour redemarrer : .\scripts\start-stack.ps1" -ForegroundColor White
Write-Host ""
