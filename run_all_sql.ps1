$ErrorActionPreference = "Stop"

$CONTAINER = "oracle_db"
$USER = "finsecure"
$PASS = "ChangeMeFinSecure2026"
$SERVICE = "XEPDB1"
$CONN = "${USER}/${PASS}@//localhost:1521/${SERVICE}"

# Ordre des scripts (01_grants en dernier, 00_init d?j? pass?)
$SCRIPTS = @(
    "02_sequences.sql",
    "03_tables.sql",
    "04_indexes.sql",
    "05_views.sql",
    "06_materialized_views.sql",
    "07_packages_plsql.sql",
    "08_triggers.sql",
    "01_grants.sql"
)

foreach ($script in $SCRIPTS) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "  Execution de $script" -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    docker exec $CONTAINER bash -c "sqlplus -s $CONN @/tmp/sql/$script"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ECHEC sur $script" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Tous les scripts ont ete executes avec succes." -ForegroundColor Green
