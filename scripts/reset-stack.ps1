# =============================================================================
# scripts/reset-stack.ps1
# =============================================================================
# DESTRUCTIF : supprime les conteneurs ET les volumes (toutes les donnees).
# A utiliser uniquement pour repartir de zero.
#
# Necessite une double confirmation pour eviter les accidents.
#
# Usage :
#   .\scripts\reset-stack.ps1
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Red
Write-Host "  RESET COMPLET DE LA STACK" -ForegroundColor Red
Write-Host "==========================================" -ForegroundColor Red
Write-Host ""
Write-Host "Ceci va SUPPRIMER :" -ForegroundColor Yellow
Write-Host "  - Les conteneurs Oracle, MongoDB, Mongo Express" -ForegroundColor Yellow
Write-Host "  - Les volumes Docker (TOUTES LES DONNEES)" -ForegroundColor Yellow
Write-Host "  - 22,5 M lignes Oracle et 100k documents MongoDB" -ForegroundColor Yellow
Write-Host ""
Write-Host "Cette operation est IRREVERSIBLE." -ForegroundColor Red
Write-Host ""

$confirm1 = Read-Host "Tape 'RESET' (en majuscules) pour confirmer"
if ($confirm1 -ne 'RESET') {
    Write-Host "Annulation. Aucune modification effectuee." -ForegroundColor Green
    exit 0
}

$confirm2 = Read-Host "Vraiment sur ? Tape 'OUI JE CONFIRME'"
if ($confirm2 -ne 'OUI JE CONFIRME') {
    Write-Host "Annulation. Aucune modification effectuee." -ForegroundColor Green
    exit 0
}

Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "Reset en cours..." -ForegroundColor Yellow

# down -v supprime les conteneurs ET les volumes du compose
docker compose down -v

# Les volumes external ne sont pas supprimes par compose, on les force
docker volume rm finsecure_oracle_data finsecure_mongo_data 2>$null

Write-Host ""
Write-Host "Reset termine. Tous les conteneurs et volumes supprimes." -ForegroundColor Green
Write-Host ""
Write-Host "Pour repartir de zero :" -ForegroundColor Yellow
Write-Host "  1. Relancer la migration Oracle complete (~6h)" -ForegroundColor White
Write-Host "  2. Relancer la migration MongoDB" -ForegroundColor White
Write-Host "  Voir README.md pour la procedure complete." -ForegroundColor White
Write-Host ""
