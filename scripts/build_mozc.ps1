<#
.SYNOPSIS
  Apply the AI rewriter patch and build a Windows Mozc target.

.DESCRIPTION
  The prototype intentionally does not vendor a Mozc checkout.  Pass the
  path to a separate checkout.  Without -ApplyPatch this script is read-only
  with respect to the checkout and runs git apply --check before building.
  Use -RunTests to build the rewriter test target first.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$MozcRoot,
  [string]$Target = '//src/server:mozc_server_win',
  [switch]$ApplyPatch,
  [switch]$RunTests,
  [switch]$VerifyOnly
)

$ErrorActionPreference = 'Stop'
$PrototypeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$MozcRoot = (Resolve-Path $MozcRoot).Path
$Patch = Join-Path $PrototypeRoot 'mozc\current_mozc.patch'

if (-not (Test-Path (Join-Path $MozcRoot '.git'))) {
  throw "MozcRoot is not a Git checkout: $MozcRoot"
}
if (-not (Test-Path $Patch)) {
  throw "Patch not found: $Patch"
}

Write-Host "Mozc checkout: $MozcRoot"
Write-Host "Patch check: $Patch"
& git -C $MozcRoot apply --check -- $Patch
if ($LASTEXITCODE -ne 0) {
  throw 'git apply --check failed; checkout was not modified'
}

if ($ApplyPatch) {
  & git -C $MozcRoot apply -- $Patch
  if ($LASTEXITCODE -ne 0) {
    throw 'git apply failed'
  }
  Write-Host 'AI rewriter patch applied.'
}

if ($VerifyOnly) {
  Write-Host 'Verification complete; build skipped.'
  exit 0
}

$Bazel = Get-Command bazelisk -ErrorAction SilentlyContinue
if (-not $Bazel) { $Bazel = Get-Command bazel -ErrorAction SilentlyContinue }
if (-not $Bazel) {
  throw 'Bazel/Bazelisk was not found on PATH. Install the Mozc Windows build prerequisites first.'
}

if ($RunTests) {
  & $Bazel.Source 'test' '//src/rewriter:ai_rewriter_test'
  if ($LASTEXITCODE -ne 0) { throw 'ai_rewriter_test failed' }
}

Write-Host "Building $Target ..."
& $Bazel.Source 'build' $Target '--define=windows_build=true'
if ($LASTEXITCODE -ne 0) {
  throw "Mozc build failed: $Target"
}
Write-Host "MOZC_BUILD_PASS: $Target"
