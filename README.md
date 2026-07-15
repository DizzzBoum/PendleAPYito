# PendleAPYito (PAO)

Desk manuel pour analyser les opportunités [Pendle Finance](https://app.pendle.finance) : scan des marchés PT/LP, comparaison d'APY, et deeplinks vers l'exécution manuelle sur l'app officielle Pendle.

## Prérequis

- Python 3.11 ou supérieur
- Git

## Installation

1. Clone le dépôt :
   ```
   git clone https://github.com/DizzzBoum/PendleAPYito
   cd PendleAPYitot
   ```
2. Lance `first_run.bat` (double-clic ou depuis un terminal). Il vérifie Python et Git, crée l'environnement virtuel `.venv` et installe les dépendances.
3. si git est a intaller :
   
   a. Éditeur → choisir " use Notepad "
   
   <img width="593" height="457" alt="image" src="https://github.com/user-attachments/assets/12963e9e-c05f-44ae-a720-3a621ff332f2" />
   
   b.  git pull behavior → choisir " Fast-forward only "
   
   <img width="591" height="457" alt="image" src="https://github.com/user-attachments/assets/97d49eb8-4ec1-476c-842c-8a22816531bc" />

   Tout le reste : Next Next Next.
4. Ouvre le fichier `.env` créé automatiquement (à partir de `.env.example`).
5. Lance `run.bat` pour démarrer l'application.

## Configuration `.env`

Le fichier `.env` est créé automatiquement par `first_run.bat` depuis `.env.example`.
Il contient déjà des endpoints RPC publics gratuits — **aucune configuration obligatoire pour démarrer.**

### Option A — Démarrage immédiat (endpoints publics)
Rien à faire. Les RPC publics dans `.env.example` fonctionnent directement.
Adapté pour découvrir PAO et analyser les marchés Pendle.

### Option B — Endpoints Alchemy (recommandé pour un usage régulier)
Les endpoints publics peuvent être lents ou instables.
Pour plus de fiabilité :

1. Crée un compte gratuit sur [alchemy.com](https://alchemy.com) (sans CB, no parrainage)
2. Crée une "app" pour chaque réseau que tu veux utiliser
3. Copie l'URL RPC complète dans la variable correspondante de `.env`


## Lancement

Double-clique sur `run.bat` (ou lance-le depuis un terminal). L'application Streamlit s'ouvre dans ton navigateur.

## Mise à jour

Un bouton de mise à jour est disponible directement dans l'application — la mise à jour se fait automatiquement depuis l'interface, pas besoin de manipulation manuelle.

## Limitations connues

Certaines fonctionnalités (prix temps réel, estimation de gas, validation de transaction) reposent sur des kits internes développés en local par le mainteneur, non publiés publiquement. Sans eux, l'application fonctionne normalement mais avec ces fonctionnalités désactivées.

## Note importante

PAO est un **desk manuel**. Aucune transaction automatique n'est effectuée. L'exécution se fait manuellement sur [app.pendle.finance](https://app.pendle.finance) via un deeplink généré par l'application.

## Soutenir le projet

PendleAPYito (PAO) est gratuit et open source.  
Si il t'est utile, tu peux soutenir le développement :

**Adresse wallet** (Ethereum, Base, Arbitrum) :  
`0x9602Ac4E681D11Ff5dcA4a076BfeEFBb09e2fFbD`

Tout token ERC-20 accepté sur ces réseaux. Merci ! 🙏
