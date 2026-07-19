# PendleAPYito (PAO)

Desk manuel pour analyser les opportunités [Pendle Finance](https://app.pendle.finance) : scan des marchés PT/LP, comparaison d'APY, et deeplinks vers l'exécution manuelle sur l'app officielle Pendle.

## PRÉREQUIS (à installer une seule fois)

1. Python 3.11+
   → https://www.python.org/downloads/
   ⚠️ Coche bien "Add Python to PATH" lors de l'installation

2. Git for Windows
   → https://git-scm.com/download/win
   Pendant l'installation, 2 écrans à modifier :
   - Éditeur : choisir "Use Notepad as Git's default editor"
     
      <img width="593" height="457" alt="image" src="https://github.com/user-attachments/assets/12963e9e-c05f-44ae-a720-3a621ff332f2" />
      
   - git pull behavior : choisir "Fast-forward only"
  
      <img width="591" height="457" alt="image" src="https://github.com/user-attachments/assets/97d49eb8-4ec1-476c-842c-8a22816531bc" />
      
   Tout le reste : Next jusqu'à la fin.

───────────────────────────────────────

## INSTALLATION PAO

Ouvre un terminal Windows (CMD ou PowerShell) et tape :

   git clone https://github.com/DizzzBoum/PendleAPYito

Puis entre dans le dossier :

   cd PendleAPYito

Double-clique sur first_run.bat
→ Il installe tout automatiquement (venv, dépendances, .env)

───────────────────────────────────────

## CONFIGURATION

Ouvre le fichier .env avec un éditeur de texte.
Les endpoints RPC publics sont déjà remplis — 
tu peux démarrer sans rien changer.

Optionnel : remplace les RPC publics par tes propres 
URLs Alchemy (gratuit) pour plus de fiabilité.
sur [alchemy.com](https://alchemy.com) (sans CB, no parrainage)

───────────────────────────────────────

## LANCEMENT

Double-clique sur run.bat
→ L'application s'ouvre dans ton navigateur sur localhost:8501

───────────────────────────────────────

## MISES À JOUR

Un bandeau apparaît dans l'app quand une mise à jour 
est disponible. Clique sur "⬇ Mettre à jour" — 
c'est automatique, pas besoin de terminal.

───────────────────────────────────────

## Soutenir le projet

PendleAPYito (PAO) est gratuit et open source.  
Si il t'est utile, tu peux soutenir le développement :

**Adresse wallet** (Ethereum, Base, Arbitrum) :  
`0x9602Ac4E681D11Ff5dcA4a076BfeEFBb09e2fFbD`

Tout token ERC-20 accepté sur ces réseaux. Merci ! 🙏

## Limitations connues

Certaines fonctionnalités (prix temps réel, estimation de gas, validation de transaction) reposent sur des kits internes développés en local par le mainteneur, non publiés publiquement. Sans eux, l'application fonctionne normalement mais avec ces fonctionnalités désactivées.

## Note importante

PAO est un **desk manuel**. Aucune transaction automatique n'est effectuée. L'exécution se fait manuellement sur [app.pendle.finance](https://app.pendle.finance) via un deeplink généré par l'application.

