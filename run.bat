@echo off
chcp 65001 >nul
setlocal

echo === PendleAPYito (PAO) — Lancement ===
echo.

if not exist ".venv\" (
    echo [ERREUR] Environnement virtuel introuvable.
    echo Lance first_run.bat d'abord.
    pause
    exit /b 1
)

call .venv\Scripts\activate

python -m streamlit run app.py

pause
