# Installation de PendleAPYito (PAO)

Desk manuel pour analyser les opportunités [Pendle Finance](https://app.pendle.finance) : scan des marchés PT/LP, comparaison d'APY, et deeplinks vers l'exécution manuelle sur l'app officielle Pendle.

## Prérequis (à installer une seule fois)

1. Python 3.11+
   → https://www.python.org/downloads/
   ⚠️ Coche bien "Add Python to PATH" lors de l'installation

2. Git for Windows
   → https://git-scm.com/download/win
   Pendant l'installation, 2 écrans à modifier :
   - Éditeur : choisir "Use Notepad as Git's default editor"
   - git pull behavior : choisir "Fast-forward only"
   Tout le reste : Next jusqu'à la fin.


## Installation

1. Ouvre un terminal Windows (CMD ou PowerShell) et tape :

   git clone https://github.com/DizzzBoum/PendleAPYito

2. Puis entre dans le dossier :

   cd PendleAPYito

3. Dans le new dossier créé PendleAPYito 
   Double-clique sur first_run.bat
→ Il installe tout automatiquement (venv, dépendances, .env).

   streamlit peut demander un email a l'installation pour la premiere fois. Appuyer sur ENTER directement, sauf si vous voulez le mettre pour des news de Streamlit.

## Configuration `.env`

Tu peux démarrer sans rien changer.
Les endpoints RPC publics sont déjà remplis

Optionnel : 
Ouvre le fichier .env avec un éditeur de texte.
remplace les RPC publics par tes propres
URLs Alchemy (alchemy.com, gratuit) pour plus de fiabilité.

## Lancement

Double-clique sur run.bat
→ L'application s'ouvre dans ton navigateur sur localhost:8501

## Mise à jour

Un bouton de mise à jour est disponible directement dans l'application — la mise à jour se fait automatiquement depuis l'interface, pas besoin de manipulation manuelle.

## Limitations connues

Certaines fonctionnalités (prix temps réel, estimation de gas, validation de transaction) reposent sur des kits internes développés en local par le mainteneur, non publiés publiquement. Sans eux, l'application fonctionne normalement mais avec ces fonctionnalités désactivées.

## Support

PendlAPYito est bien openSource/Gratuit

Wallet (dons) — Ethereum / Base / Arbitrum :
0x9602Ac4E681D11Ff5dcA4a076BfeEFBb09e2fFbD
