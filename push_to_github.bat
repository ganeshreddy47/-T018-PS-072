@echo off
echo ========================================================
echo Pushing T018-PS-072 to GitHub Repository
echo Repository: https://github.com/ganeshreddy47/-T018-PS-072
echo ========================================================

cd /d "%~dp0"

if not exist .git (
    echo Initializing Git repository...
    git init
    git branch -M main
    git remote add origin https://github.com/ganeshreddy47/-T018-PS-072.git
)

echo Adding all files...
git add .

echo Committing...
git commit -m "Complete PS-072 Result Engine implementation: engine, tests, documentation, sample data, and evaluation outputs (Team T018)"

echo Pushing to main branch...
git push -u origin main

echo Done!
pause
