@echo off
title FitQuest - Push to GitHub
echo ========================================================
echo Pushing FitQuest Commits to GitHub...
echo ========================================================
echo.
cd /d "%~dp0"
git push origin main
echo.
if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo SUCCESS! Commits pushed to GitHub.
    echo Vercel will now automatically build and deploy.
    echo In ~60 seconds, your site will be updated at:
    echo https://fitquest-frontend-one.vercel.app
    echo ========================================================
) else (
    echo ========================================================
    echo Push did not complete. If prompted, please sign in to GitHub.
    echo ========================================================
)
echo.
pause
