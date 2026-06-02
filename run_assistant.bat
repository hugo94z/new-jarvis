@echo off
title Assistant Vocal Agentique DeepSeek
echo Demarrage de l'Assistant Vocal...
cd /d "c:\Users\Boyz\Desktop\Nouveau dossier (13)"
python app.py
if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] L'assistant s'est arrete avec une erreur.
    pause
)
