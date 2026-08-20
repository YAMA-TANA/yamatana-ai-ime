[CmdletBinding()]
param(
  [string]$ManifestPath,
  [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ManifestPath) { $ManifestPath = Join-Path $RepoRoot 'model-manifest.json' }
$ManifestPath = (Resolve-Path $ManifestPath).Path
$Manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json

if ($Manifest.schema -ne 1) { throw "Unsupported model manifest schema: $($Manifest.schema)" }
if ($Manifest.bundle.sha256 -notmatch '^[0-9A-Fa-f]{64}$') { throw 'Invalid bundle SHA-256' }
foreach ($entry in $Manifest.files) {
  if ($entry.path -match '(^|/|\\)\.\.($|/|\\)' -or [IO.Path]::IsPathRooted($entry.path)) {
    throw "Unsafe manifest path: $($entry.path)"
  }
  if ($entry.sha256 -notmatch '^[0-9A-Fa-f]{64}$') { throw "Invalid SHA-256: $($entry.path)" }
}

if ($VerifyOnly) {
  Write-Host "MODEL_MANIFEST_OK: $($Manifest.bundle.version)"
  exit 0
}

$DownloadDir = Join-Path $RepoRoot 'build\downloads'
New-Item -ItemType Directory -Force -Path $DownloadDir | Out-Null
$Archive = Join-Path $DownloadDir ([IO.Path]::GetFileName([Uri]$Manifest.bundle.url))

if (-not (Test-Path -LiteralPath $Archive)) {
  Write-Host "Downloading pinned model bundle $($Manifest.bundle.version)..."
  Invoke-WebRequest -Uri $Manifest.bundle.url -OutFile $Archive
}

$ArchiveItem = Get-Item -LiteralPath $Archive
if ($ArchiveItem.Length -ne [int64]$Manifest.bundle.bytes) {
  throw "Model bundle size mismatch: expected $($Manifest.bundle.bytes), got $($ArchiveItem.Length)"
}
$ArchiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Archive).Hash
if ($ArchiveHash -ne $Manifest.bundle.sha256.ToUpperInvariant()) {
  throw "Model bundle SHA-256 mismatch: $ArchiveHash"
}

$ExtractDir = Join-Path $DownloadDir ("extract-" + $Manifest.bundle.sha256.Substring(0, 16))
if (-not (Test-Path -LiteralPath $ExtractDir)) {
  New-Item -ItemType Directory -Path $ExtractDir | Out-Null
  Expand-Archive -LiteralPath $Archive -DestinationPath $ExtractDir
}

foreach ($entry in $Manifest.files) {
  $relative = $entry.path.Replace('/', [IO.Path]::DirectorySeparatorChar)
  $source = Join-Path $ExtractDir $relative
  if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw "Missing bundle file: $($entry.path)" }
  $sourceItem = Get-Item -LiteralPath $source
  $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
  if ($sourceItem.Length -ne [int64]$entry.bytes -or $sourceHash -ne $entry.sha256.ToUpperInvariant()) {
    throw "Model file verification failed: $($entry.path)"
  }
  if ($entry.path -eq 'MODEL_CARD.md') { continue }
  $destination = Join-Path $RepoRoot $relative
  New-Item -ItemType Directory -Force -Path (Split-Path $destination -Parent) | Out-Null
  Copy-Item -LiteralPath $source -Destination $destination -Force
}

Write-Host "MODEL_FETCH_PASS: $($Manifest.bundle.version) $ArchiveHash"
