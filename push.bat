@echo off
setlocal EnableDelayedExpansion

echo ========================================================
echo   PayResolve AI — Automated GitHub Push Utility
echo ========================================================
echo.

:: 1. Safety Check: Ensure .env is never tracked
git ls-files --error-unmatch .env >nul 2>&1
if %errorlevel% equ 0 (
    echo [SECURITY STOP] .env is currently tracked by Git! Removing from index...
    git rm --cached .env
)

:: 2. Check for changes
git status -s
for /f %%i in ('git status --porcelain') do set HAS_CHANGES=1

if not defined HAS_CHANGES (
    echo.
    echo [*] No uncommitted file changes found. Checking if local commits need pushing...
    for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
    git push -u origin !BRANCH!
    goto :eof
)

echo.

:: 3. Determine commit message (from CLI argument or interactive prompt with default)
set "COMMIT_MSG=%~1"

if "!COMMIT_MSG!"=="" (
    set "DEFAULT_MSG=Update PayResolve AI multi-agent swarm and visualizer (%date% %time:~0,5%)"
    echo Press [ENTER] to use default message:
    echo   "!DEFAULT_MSG!"
    echo Or type your custom commit message below:
    set /p "USER_MSG=> "
    if "!USER_MSG!"=="" (
        set "COMMIT_MSG=!DEFAULT_MSG!"
    ) else (
        set "COMMIT_MSG=!USER_MSG!"
    )
)

echo.
echo [1/3] Staging all changes (git add -A)...
git add -A

:: Double check .env is not staged
git reset HEAD .env >nul 2>&1

echo [2/3] Committing with message: "!COMMIT_MSG!"...
git commit -m "!COMMIT_MSG!"
if %errorlevel% neq 0 (
    echo [ERROR] Git commit failed.
    exit /b 1
)

for /f "tokens=*" %%b in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%b
echo [3/3] Pushing to GitHub (origin/!BRANCH!)...
git push -u origin !BRANCH!
if %errorlevel% neq 0 (
    echo [ERROR] Git push failed. Check your network or GitHub credentials.
    exit /b 1
)

echo.
echo [SUCCESS] Successfully pushed to GitHub (origin/!BRANCH!)!
endlocal

