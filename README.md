# PendleAPYito (PAO)

Desk manuel pour analyser les opportunités [Pendle Finance](https://app.pendle.finance) : scan des marchés PT/LP, comparaison d'APY, et deeplinks vers l'exécution manuelle sur l'app officielle Pendle.

## Prérequis

- Python 3.11 ou supérieur
- Git

## Installation

1. Clone le dépôt :
   ```
   git clone <url-du-repo>
   cd PendleAPYitot
   ```
2. Lance `first_run.bat` (double-clic ou depuis un terminal). Il vérifie Python et Git, crée l'environnement virtuel `.venv` et installe les dépendances.
3. Ouvre le fichier `.env` créé automatiquement (à partir de `.env.example`).
4. Édite `.env` et remplis au moins tes clés RPC (voir section suivante).
5. Lance `run.bat` pour démarrer l'application.

## Configuration `.env`

PAO a besoin d'endpoints RPC pour interroger les réseaux blockchain. La façon la plus simple d'en obtenir gratuitement :

1. Crée un compte gratuit sur [alchemy.com](https://www.alchemy.com/).
2. Pour chaque réseau que tu veux utiliser (Ethereum, Arbitrum, Base, Optimism, BNB, Monad, Plasma, Hyperliquid), crée une "app" Alchemy et copie l'URL RPC complète.
3. Colle chaque URL dans la variable correspondante de `.env` (`RPC_ETHEREUM`, `RPC_ARBITRUM`, etc.).

Tu peux laisser vide un réseau que tu n'utilises pas. Les autres variables (`FEE_MAX_USD_PER_TX`, couleurs `UI_*`) ont des valeurs par défaut raisonnables si tu ne les remplis pas.

## Lancement

Double-clique sur `run.bat` (ou lance-le depuis un terminal). L'application Streamlit s'ouvre dans ton navigateur.

## Mise à jour

Un bouton de mise à jour est disponible directement dans l'application — la mise à jour se fait automatiquement depuis l'interface, pas besoin de manipulation manuelle.

## Limitations connues

Certaines fonctionnalités (prix temps réel, estimation de gas, validation de transaction) reposent sur des kits internes développés en local par le mainteneur, non publiés publiquement. Sans eux, l'application fonctionne normalement mais avec ces fonctionnalités désactivées.

## Note importante

PAO est un **desk manuel**. Aucune transaction automatique n'est effectuée. L'exécution se fait manuellement sur [app.pendle.finance](https://app.pendle.finance) via un deeplink généré par l'application.
