<# Creates a consistent SQLite backup and retains the newest seven pairs. #>
param([string]$DatabasePath = "")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $DatabasePath) { $DatabasePath = Join-Path $root "data\mathmind.db" }
$DatabasePath = [System.IO.Path]::GetFullPath($DatabasePath)
if (-not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
    throw "Source database does not exist: $DatabasePath"
}

$backupDirectory = Join-Path $root "data\backups"
New-Item -ItemType Directory -Force -Path $backupDirectory | Out-Null
$backupPath = Join-Path $backupDirectory ("mathmind-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".db")
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command py -ErrorAction SilentlyContinue }
if (-not $python) { throw "Python is required for SQLite backups" }

$backupCode = @'
import hashlib
import os
import sqlite3
import sys

source_path, backup_path = sys.argv[2:4]
source = sqlite3.connect(source_path)
destination = sqlite3.connect(backup_path)
try:
    source.backup(destination)
finally:
    destination.close()
    source.close()

digest = hashlib.sha256()
with open(backup_path, "rb") as backup_file:
    for chunk in iter(lambda: backup_file.read(1024 * 1024), b""):
        digest.update(chunk)
with open(backup_path + ".sha256", "w", encoding="ascii", newline="\n") as checksum_file:
    checksum_file.write(f"{digest.hexdigest()}  {os.path.basename(backup_path)}\n")
'@

try {
    $encodedBackupCode = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($backupCode))
    & $python.Source -c "import base64,sys;exec(base64.b64decode(sys.argv[1]))" $encodedBackupCode $DatabasePath $backupPath
    if ($LASTEXITCODE -ne 0) { throw "SQLite backup failed with exit code $LASTEXITCODE" }
    Get-ChildItem -LiteralPath $backupDirectory -Filter "mathmind-*.db" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -Skip 7 |
        ForEach-Object {
            Remove-Item -LiteralPath $_.FullName -Force
            $checksumPath = "$($_.FullName).sha256"
            if (Test-Path -LiteralPath $checksumPath -PathType Leaf) { Remove-Item -LiteralPath $checksumPath -Force }
        }
    Write-Host "Backup created: $backupPath"
}
catch {
    Write-Error $_
    exit 1
}
