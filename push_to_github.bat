@echo off
echo ========================================================
echo Pushing T018-PS-072 to GitHub Repository
echo Repository: https://github.com/ganeshreddy47/-T018-PS-072
echo ========================================================

cd /d "%~dp0"

set "PATH=%PATH%;C:\Users\dhanu\.gemini\antigravity\scratch\mingit\cmd"

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Git not found.
    pause
    exit /b 1
)

echo Adding remote origin if needed...
git remote remove origin 2>nul
git remote add origin https://github.com/ganeshreddy47/-T018-PS-072.git

echo Ensuring all files are added and committed...
git add .
git commit -m "Complete PS-072 Result Engine implementation: engine, tests, documentation, sample data, and evaluation outputs (Team T018)" 2>nul

echo.
echo Pushing to GitHub (you may be prompted for your GitHub credentials / Personal Access Token)...
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo SUCCESS! Repository successfully pushed to GitHub:
    echo https://github.com/ganeshreddy47/-T018-PS-072
    echo ========================================================
) else (
    echo.
    echo Pushing failed. Please check your GitHub credentials or internet connection.
)

pause
