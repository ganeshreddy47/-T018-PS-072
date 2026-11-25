# PowerShell script to push project to GitHub
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Pushing T018-PS-072 to GitHub Repository" -ForegroundColor Cyan
Write-Host "Repository: https://github.com/ganeshreddy47/-T018-PS-072" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Add MinGit to PATH for this session
$env:Path += ";C:\Users\dhanu\.gemini\antigravity\scratch\mingit\cmd"

# Check git
try {
    & git --version | Out-Null
} catch {
    Write-Host "Error: Git could not be located." -ForegroundColor Red
    exit 1
}

# Ensure remote is set
& git remote remove origin 2>$null
& git remote add origin https://github.com/ganeshreddy47/-T018-PS-072.git

# Stage and commit
& git add .
& git commit -m "Complete PS-072 Result Engine implementation: engine, tests, documentation, sample data, and evaluation outputs (Team T018)" 2>$null

Write-Host "Pushing to GitHub (you may be prompted for your GitHub credentials / Personal Access Token)..." -ForegroundColor Yellow
& git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n========================================================" -ForegroundColor Green
    Write-Host "SUCCESS! Repository successfully pushed to GitHub:" -ForegroundColor Green
    Write-Host "https://github.com/ganeshreddy47/-T018-PS-072" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Green
} else {
    Write-Host "`nPush failed. Please verify your GitHub credentials." -ForegroundColor Red
}
