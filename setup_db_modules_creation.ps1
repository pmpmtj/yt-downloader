<# 
Usage examples:
  # Basic (prompts for password via -W)
  .\setup_db_modules_creation.ps1 -ProjectRoot . -MarkdownPath .\db_modules_creation.md -DbName yt_app -DbUser postgres

  # Custom host/port and force drop+recreate:
  .\setup_db_modules_creation.ps1 -ProjectRoot . -MarkdownPath .\db_modules_creation.md -DbName yt_app -DbUser postgres -DbHost localhost -Port 5432 -DropRecreate

  # Only create files (skip DB work):
  .\setup_db_modules_creation.ps1 -ProjectRoot . -MarkdownPath .\db_modules_creation.md -DbName yt_app -DbUser postgres -OnlyFiles
#>

[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)] [string]$ProjectRoot,
  [Parameter(Mandatory=$true)] [string]$MarkdownPath,

  [string]$DbName = "yt_app",
  [string]$DbUser = "postgres",
  [string]$DbHost = "localhost",
  [int]   $Port   = 5432,

  [switch]$DropRecreate,
  [switch]$OnlyFiles
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Section($msg) {
  Write-Host ""
  Write-Host ("=" * 80)
  Write-Host "  $msg"
  Write-Host ("=" * 80)
}

# Helper: always write UTF-8 *without BOM*
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
}

# ----- psql helpers: ALWAYS pass args as an ARRAY ------------------------------
function Get-PsqlBaseArgs {
    param([string]$Db = $null)
    $args = @("-h", $DbHost, "-p", $Port.ToString(), "-U", $DbUser, "-W")
    if ($Db) { $args += @("-d", $Db) }
    return ,$args  # force as object[] not string
}

function Invoke-PsqlCommand {
    param([string]$Sql, [string]$Db = $null, [switch]$Quiet)
    $args = Get-PsqlBaseArgs -Db $Db
    # -v ON_ERROR_STOP=1 makes psql stop on first SQL error
    $args += @("-v","ON_ERROR_STOP=1","-c",$Sql)
    if (-not $Quiet) { Write-Host "Running: psql $($args -join ' ')" }
    & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql command failed with exit code $LASTEXITCODE" }
}

function Invoke-PsqlFile {
    param([string]$FilePath, [string]$Db)
    if (!(Test-Path $FilePath)) { throw "SQL file not found: $FilePath" }
    $args = Get-PsqlBaseArgs -Db $Db
    $args += @("-v","ON_ERROR_STOP=1","-f",$FilePath)
    Write-Host "Running: psql $($args -join ' ')"
    & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql file exec failed with exit code $LASTEXITCODE" }
}

function Test-DatabaseExists {
    $args = Get-PsqlBaseArgs
    # Use -t -A and a simple SELECT, return True/False
    $args += @("-t","-A","-c","SELECT 1 FROM pg_database WHERE datname = '$DbName';")
    $out = & psql @args
    if ($LASTEXITCODE -ne 0) { throw "psql check failed with exit code $LASTEXITCODE" }
    return ($out -match "^1\s*$")
}

# -- 1) Read and parse the markdown for file paths + code blocks ----------------
Write-Section "Step 1: Creating files from markdown ($MarkdownPath)"
if (!(Test-Path $MarkdownPath)) { throw "Markdown file not found: $MarkdownPath" }
$md = Get-Content -Raw -LiteralPath $MarkdownPath

# Matches:
#   **Location**: `path`  ...  ```<lang>\nCODE\n```
#   **New File**: `path`  ...  ```<lang>\nCODE\n```
$pattern = '(?ms)\*\*(Location|New File)\*\*:\s*`([^`]+)`.*?```(?:[a-zA-Z0-9_+\-]*)\r?\n(.*?)\r?\n```'
$matches = [regex]::Matches($md, $pattern)

if ($matches.Count -eq 0) {
  Write-Warning "No code blocks with **Location**/**New File** found in markdown."
} else {
  foreach ($m in $matches) {
    $relPath = $m.Groups[2].Value.Trim()
    $code    = $m.Groups[3].Value

    $fullPath = Join-Path -Path $ProjectRoot -ChildPath $relPath
    $dir = Split-Path -Path $fullPath -Parent
    if (!(Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }

    Write-Utf8NoBom -Path $fullPath -Content $code
    Write-Host "Wrote: $fullPath"
  }
}

# Try to locate schema.sql path from the markdown; fall back to common default
$schemaPathFromMd = $null
foreach ($m in $matches) {
  $p = $m.Groups[2].Value.Trim()
  if ($p -match 'schema\.sql$') { $schemaPathFromMd = $p; break }
}
if (-not $schemaPathFromMd) {
  $schemaPathFromMd = "my_project/src/my_project/db/schema.sql"
}
$schemaFullPath = Join-Path $ProjectRoot $schemaPathFromMd
Write-Host "Detected schema path: $schemaFullPath"

# -- 2) Ensure minimal .env (no password is stored) ----------------------------
Write-Section "Step 2: Writing minimal .env (no password)"
$envPath = Join-Path $ProjectRoot ".env"
if (!(Test-Path $envPath)) {
  $dbUrl = "postgresql+psycopg://$DbUser@$DbHost`:$Port/$DbName"
  $envContent = @"
DATABASE_ENABLED=true
DATABASE_URL=$dbUrl
"@
  Write-Utf8NoBom -Path $envPath -Content $envContent
  Write-Host "Created .env -> $envPath"
} else {
  Write-Host ".env already exists; leaving it unchanged."
}

if ($OnlyFiles) {
  Write-Host "OnlyFiles flag set. Skipping DB steps."
  exit 0
}

# -- 3) DB work: create DB (or drop+recreate), then run schema ------------------
Write-Section "Step 3: PostgreSQL admin (you will be prompted for the password)"

if ($DropRecreate) {
  Invoke-PsqlCommand -Sql "DROP DATABASE IF EXISTS $DbName;" -Db $null
  Invoke-PsqlCommand -Sql "CREATE DATABASE $DbName;" -Db $null
} else {
  $exists = Test-DatabaseExists
  if (-not $exists) {
    Invoke-PsqlCommand -Sql "CREATE DATABASE $DbName;" -Db $null
  } else {
    Write-Host "Database '$DbName' already exists; skipping creation."
  }
}

# Apply schema
Invoke-PsqlFile -FilePath $schemaFullPath -Db $DbName

Write-Section "All done!"
Write-Host "Files created from markdown."
Write-Host "Database ensured and schema applied."
