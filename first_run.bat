@echo off
chcp 65001 >nul
setlocal

echo === PendleAPYito (PAO) — Installation ===
echo.

REM --- Verification de Python ---
py --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou introuvable dans le PATH.
    echo Ouverture de la page de telechargement Python...
    start https://www.python.org/downloads/
    echo.
    echo IMPORTANT : coche "Add Python to PATH" pendant l'installation.
    echo Relance ensuite ce script.
    pause
    exit /b 1
)

REM --- Verification de Git ---
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Git n'est pas installe ou introuvable dans le PATH.
    echo Ouverture de la page de telechargement Git...
    start https://git-scm.com/download/win
    pause
    exit /b 1
)

REM --- Creation de l'environnement virtuel ---
if not exist ".venv\" (
    echo Creation de l'environnement virtuel .venv...
    py -m venv .venv
) else (
    echo Environnement virtuel .venv deja present.
)

REM --- Activation du venv ---
call .venv\Scripts\activate

REM --- Installation des dependances ---
echo Mise a jour de pip...
python -m pip install --upgrade pip

echo Installation des dependances (requirements.txt)...
pip install -r requirements.txt

REM --- Creation du .env a partir du template ---
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Fichier .env cree a partir de .env.example.
    )
) else (
    echo Fichier .env deja present, non modifie.
)

echo.
echo ✅ Installation terminee ! Ouvre .env, remplis tes cles RPC Alchemy (alchemy.com gratuit), puis lance run.bat
echo.
pause
