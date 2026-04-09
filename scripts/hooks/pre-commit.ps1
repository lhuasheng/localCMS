# pre-commit hook (PowerShell): validates backlinks before allowing a commit.
# Install: run scripts\install-hooks.ps1 from the repo root.
# Bypass:  git commit --no-verify

$ErrorActionPreference = "Stop"

Write-Host "[pre-commit] Running cms validate-backlinks..."

# Resolve the repo root and change into it.
$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

$output = & cms validate-backlinks 2>&1
$exitCode = $LASTEXITCODE

Write-Host $output

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "[pre-commit] ✗ Backlink validation failed. Fix the issues above before committing."
    Write-Host "             To skip this check (not recommended): git commit --no-verify"
    exit 1
}

Write-Host "[pre-commit] ✓ Backlink validation passed."
exit 0
