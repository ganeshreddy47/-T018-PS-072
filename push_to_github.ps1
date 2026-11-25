# PowerShell script to push project to GitHub
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Pushing T018-PS-072 to GitHub Repository" -ForegroundColor Cyan
Write-Host "Repository: https://github.com/ganeshreddy47/-T018-PS-072" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

if (-not (Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    git branch -M main
    git remote add origin https://github.com/ganeshreddy47/-T018-PS-072.git
}

Write-Host "Staging files..." -ForegroundColor Yellow
git add .

Write-Host "Committing..." -ForegroundColor Yellow
git commit -m "Complete PS-072 Result Engine implementation: engine, tests, documentation, sample data, and evaluation outputs (Team T018)"

Write-Host "Pushing to remote repository..." -ForegroundColor Green
git push -u origin main

Write-Host "Push complete!" -ForegroundColor Green
