$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $Root
try {
  python -m unittest discover -s tests -p 'test_*.py' -v
  exit $LASTEXITCODE
}
finally {
  Pop-Location
}

