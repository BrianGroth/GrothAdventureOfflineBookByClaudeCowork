# Groth Adventures Scrapbook - Monthly Update Script (PowerShell)
# Run this script monthly to sync the latest blog posts
# Usage: .\scripts\monthly_update.ps1

param(
    [string]$Source = "grothadventures",
    [string]$DataDir = "",
    [switch]$Full = $false,
    [switch]$NoMedia = $false,
    [int]$Port = 8420
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Groth Adventures Scrapbook Update" -ForegroundColor Cyan
Write-Host " $(Get-Date -Format 'yyyy-MM-dd HH:mm')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Build command arguments
$Args = @("sync", "--source", $Source)
if ($DataDir) { $Args += @("--data-dir", $DataDir) }
if ($Full) { $Args += "--full" }
if ($NoMedia) { $Args += "--no-media" }

# Check if scrapbook is installed
try {
    $null = Get-Command "scrapbook" -ErrorAction Stop
} catch {
    Write-Host "ERROR: 'scrapbook' command not found." -ForegroundColor Red
    Write-Host "Install with: pip install -e '$ProjectDir'" -ForegroundColor Yellow
    exit 1
}

Write-Host "Step 1: Syncing latest posts from $Source..." -ForegroundColor Green
& scrapbook @Args
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Sync failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Step 2: Rebuilding search index..." -ForegroundColor Green
$indexArgs = @("reindex", "--fts", "--tags")
if ($DataDir) { $indexArgs += @("--data-dir", $DataDir) }
& scrapbook @indexArgs

Write-Host ""
Write-Host "Step 3: Status check..." -ForegroundColor Green
$statusArgs = @("status")
if ($DataDir) { $statusArgs += @("--data-dir", $DataDir) }
& scrapbook @statusArgs

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Update complete!" -ForegroundColor Green
Write-Host " View your scrapbook:" -ForegroundColor Cyan
Write-Host "   scrapbook serve --port $Port" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
