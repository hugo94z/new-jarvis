@echo off
title Assistant Vocal Agentique DeepSeek
echo ============================================================
echo   Demarrage de l'Assistant Vocal Agentique DeepSeek...
echo ============================================================
echo.
cd /d "%~dp0"
echo [INFO] Repertoire de travail : %cd%
echo [INFO] Lancement de app.py...
echo.
python app.py
if %errorlevel% neq 0 (
    echo.
    echo ============================================================
    echo [ERREUR] L'assistant s'est arrete avec une erreur.
    echo ============================================================
    echo.
    echo Verifiez que :
    echo   1. Python est installe (python --version)
    echo   2. Les dependances sont installees (pip install -r requirements.txt)
    echo   3. La cle API DeepSeek est configuree dans config.json
    echo.
    pause
)
