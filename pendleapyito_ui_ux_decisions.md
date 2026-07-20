# PendleAPYito — ui_ux_decisions.md

## Rôle de ce fichier
Ce fichier regroupe les décisions UI / UX déjà validées ou clairement exprimées pour **PendleAPYito**.  
Il sert à conserver une interface cohérente, rapide à lire et adaptée à un usage de desk manuel.

---

# 1. Intention générale de l'interface

PendleAPYito doit rester :
- **compact** ;
- **rapide à parcourir** ;
- **orienté décision** ;
- **lisible sans surcharge**.

L'interface doit aider Fanto à repérer rapidement les opportunités et à suivre les éléments importants sans devoir fouiller dans trop de sous-écrans.

---

# 2. Market Scan — UX retenue

## Objectif
Le Market Scan est un écran central de repérage rapide.

## Principes d'affichage
- Les filtres doivent rester accessibles et compréhensibles.
- Les résultats doivent être lisibles immédiatement.
- Les cas où les filtres excluent tous les marchés doivent être compréhensibles, afin d'éviter de croire à un bug si les critères sont simplement trop stricts.

## Multi-chaînes
- Selectbox "Chaîne à récupérer" positionnée en première colonne avant les boutons.
- Permet de choisir la chaîne à fetch depuis l'API Pendle.
- Liste : Ethereum, Base, BNB, Arbitrum, Optimism, HyperEVM.

## Points déjà rencontrés
- Des résultats absents pouvaient venir d'un seuil de TVL trop élevé ou d'autres filtres trop restrictifs.
- Il faut conserver un comportement transparent et lisible sur ce point.

---

# 3. Tableaux PT / LP

## Orientation visuelle
Les tableaux PT et LP doivent rester :
- séparés quand cela améliore la lecture ;
- faciles à comparer ;
- orientés vers l'action manuelle et la prise de décision.

## Décision validée
La présence de tableaux dédiés PT et LP est cohérente avec l'objectif du desk et doit être conservée tant qu'elle améliore la lisibilité.

---

# 4. Formatage des nombres

## Objectif
Les gros chiffres doivent rester rapides à interpréter.

## Décision validée
- Utiliser des formats compacts quand cela améliore la lecture :
  - par exemple `k` pour les milliers sur les volumes / TVL quand pertinent.
- Préserver une lecture claire des APY, TVL et autres métriques sans noyer l'écran.

---

# 5. Streamlit — cohérence et stabilité

## Décisions déjà intégrées ou surveillées
- Éviter les conflits de widgets Streamlit en utilisant des `key` uniques.
- Les warnings de dépréciation doivent être corrigés proprement.
- `use_container_width` doit être remplacé quand nécessaire par les nouveaux paramètres adaptés (`width="stretch"` ou équivalent selon le composant / la version).

---

# 6. Orders v2 — UX finalisée

## Orientation
Orders v2 doit produire une expérience :
- simple ;
- lisible ;
- cohérente avec un desk manuel.

## Implémentation actuelle
- **Tableau résumé en haut** avec colonnes : ID, Action, Market, Chain, Montant, Status, Âge, Créé le.
- **Colonne Âge** : format lisible (`2m`, `5h`, `12j`) avec alerte visuelle `⚠️ Xj` si > 3 jours.
- **Ronds de couleurs toujours visibles** : 🟢 OPEN, 🟡 SIMULATED, 🔴 CANCELLED (même dans détails).
- **Bouton nettoyage intelligent** : "Supprimer les X ordres > 3 jours" n'apparaît que si ordres anciens détectés.
- **Section "Détail brut"** : expandeurs par ordre avec boutons Supprimer / Simuler / Annuler conditionnels.

## Intention
L'utilisateur doit pouvoir :
- préparer un ordre ;
- visualiser son statut immédiatement ;
- retrouver facilement les ordres actifs vs anciens vs annulés ;
- comprendre rapidement leur rôle et leur état.

## À éviter
- Surcomplexifier l'écran avant que le flux de base soit stabilisé.
- Introduire trop tôt une logique d'exécution automatique dans l'interface.

---

# 7. Portfolio — UX actuelle

## Actions rapides
- Section "Actions rapides" en bas de page.
- Dropdown sélection position avec format : `PT | market | chain | qty | PnL%`.
- Carte contexte : maturité, jours restants, PnL actuel.
- Formulaire : type d'action (Vendre PT/YT, Retirer/Ajouter LP) + montant.
- Bouton "🚀 Créer l'ordre" génère un ordre depuis la position sélectionnée.

## Lecture wallet
- Champ "Adresse wallet" en haut avec bouton "Charger positions".
- Si adresse vide → mode mock (position fictive).
- Si adresse fournie → tentative fetch API Pendle (actuellement en attente d'endpoint correct).

## Montants par défaut
- Réduits à **10** pour faciliter les tests.
- Fichier : `ui/portfolio.py`, ligne ~180.

---

# 8. Montants par défaut globaux

## Décision validée
- Tous les champs montant par défaut sont à **10** au lieu de 100 ou 1000.
- Fichiers concernés :
  - `ui/actions.py` : ligne ~95
  - `ui/portfolio.py` : ligne ~180

---

# 9. Actions — sélecteur Token d'entrée (multi-stablecoins)

## Décision validée (2026-05-23)
- Un dropdown **"Token d'entrée"** a été ajouté dans l'onglet Actions.
- Choix disponibles : **USDC, USDT, DAI, USDe, FRAX**.
- Le token sélectionné est transmis à `prepare_action` et sauvegardé dans `orders.json` via le champ `stable_token`.
- Valeur par défaut : **USDC** (rétrocompatibilité totale avec les anciens ordres).
- Les ordres créés depuis le Portfolio (actions rapides) hardcodent encore `"stable_token": "USDC"` — pas de sélecteur Portfolio pour l'instant.

## Principe UI
- Le sélecteur doit rester sobre et positionné logiquement dans le formulaire d'action.
- Ne pas alourdir l'UI pour les cas simples (USDC reste le défaut).

---

# 10. Deeplinks Pendle.finance — montant dans l'URL

## État actuel (2026-05-23)
- Le paramètre `inputAmount` est maintenant inclus dans les URLs générées vers Pendle.finance.
- Exemple : `https://app.pendle.finance/trade/markets/.../swap?chain=base&inputAmount=10.0`
- **Problème ouvert** : Pendle ne reconnaît pas ce paramètre et ne pré-remplit pas le champ montant.
- Le nom exact du paramètre URL attendu par Pendle n'est pas documenté publiquement.

## Décision
- Sujet **mis en attente** : le paramètre `inputAmount` reste dans l'URL (sans effet visible pour l'instant).
- À reprendre quand le bon nom de paramètre Pendle sera identifié (via SDK, code source ou documentation future).

---

# 11. Cohérence produit

L'UI de PendleAPYito doit rester alignée avec son rôle :
- ce n'est pas un robot autonome ;
- c'est un **poste de pilotage manuel spécialisé Pendle**.

Chaque ajout visuel doit donc répondre à une question simple :
> Est-ce que cela améliore réellement la lecture, la comparaison ou la préparation d'une action manuelle ?

---

# 12. Règles de travail UI

- Préserver ce qui est déjà clair et validé.
- Privilégier les petites améliorations ciblées.
- Ne pas densifier l'interface sans bénéfice concret.
- Vérifier l'état actuel du code UI avant de proposer une modification.
- Conserver l'orientation "desk rapide et lisible".

---

# History

## 2026-06-30
- **Section "Ouvrir sur Pendle" dans l'onglet Actions** : ajoutée après le bloc Payload, additive. Affiche le montant à saisir manuellement (Pendle ne pré-remplit pas via URL), puis le deeplink selon le type d'action.
- **Comportement par type d'action** : Buy PT → bouton "Vérifier via TransactionKit" d'abord ; si OK, bouton "Ouvrir sur Pendle" + checklist consultable ; si le kit refuse (token non allowlisté), deeplink quand même proposé "malgré l'alerte". Add LP / Buy YT → deeplink direct sans validation kit (mention claire). LP pointe vers zap/in.
- **Second bouton dry-run retiré de l'UI** : `confirm_and_execute` n'est plus exposé dans l'interface (le kit sert à vérifier, pas à simuler une exécution non réalisée ici). Fonctions conservées dans le pont pour usage futur.
- **Chaînes Monad et Plasma** visibles dans les filtres Market Scan et le filtre chaîne d'Actions une fois le cache rafraîchi. Affichées en toutes lettres (monad, plasma) après ajout au chain_map.
- **Imperfection d'affichage notée** : doublons numéro/nom de chaîne (143 + monad, 9745 + plasma) dans les filtres tant que le cache n'est pas purgé. Cosmétique, sans impact (même chaîne).

## 2026-06-28
- **Tableau Market Scan allégé** : colonne `market_name` retirée de l'affichage (redondante avec `asset_symbol`). Colonne `points` déplacée en fin de tableau. Colonne `lp_max_boosted_apy` ajoutée ("LP Boost %"). market_name conservé dans les données normalisées mais non affiché.
- **Bloc "Meilleure opportunité par actif (multi-chaînes)" supprimé** : peu d'actifs présents sur plusieurs chaînes, gain de place jugé prioritaire.
- **Fiche détail marché (selectbox, choix B confirmé)** : layout 3 colonnes de métriques (APY/TVL · Maturité/Jours restants · LP Boost/Volume 24h), puis Points/Airdrop, taux de conversion, protocoles, description, risque (st.warning), particularités si non génériques (st.info), bouton "Ouvrir sur le protocole" (st.link_button). Selectbox basé sur "asset_symbol | chain" pour lever l'ambiguïté multi-chaînes.
- **Fiche détail respecte le filtre chaîne actif** : ne propose que les marchés de la chaîne sélectionnée dans Market Scan (comportement natif via `filtered`).
- **ROI retiré de l'UI** : PT ROI / YT ROI ne sont plus affichés (ni tableau ni fiche détail).
- **Clic sur ligne du tableau** : écarté. `st.dataframe` natif ne gère pas la sélection de ligne de façon fiable selon les versions. Le selectbox reste la méthode retenue (robuste, prévisible).

## 2026-06-20
- Sélecteur "Token d'entrée" dans Actions : FRAX retiré de la liste (dynamique, aucun changement de code requis côté UI).
- Choix disponibles désormais : USDC, USDT, DAI, USDe.

## 2026-05-23 — Session Claude Code CLI (v2.1.148)
Première session de travail avec **Claude Code CLI** sur le projet PendleAPYito.
- Analyse complète du projet par Claude Code : architecture, bugs, état des modules.
- **Sélecteur "Token d'entrée"** ajouté dans l'onglet Actions : USDC, USDT, DAI, USDe, FRAX.
- **Deeplinks Pendle** : paramètre `inputAmount` ajouté dans les URLs (branches LP et fallback).  
  → Problème ouvert : Pendle ne reconnaît pas ce paramètre, sujet mis en attente.

## 2026-05-20
- Bouton "Préparer" dans Orders simplifié : st.link_button direct vers Pendle.finance.
- Slippage configurable supprimé (inutile sans appel API SDK).
- session_state pour résultat préparation supprimé.
- Champ wallet pour exécution conservé pour usage futur (moteur commun).
- Décision : l'exécution reste manuelle via Pendle.finance pour l'instant.

## 2026-05-19
- Orders v2 : tableau résumé, colonne Âge, nettoyage automatique, ronds couleurs permanents.
- Portfolio : Actions rapides, champ adresse wallet, montant par défaut à 10.
- Market Scan : selectbox multi-chaînes positionnée avant boutons.
- Montants par défaut globaux réduits à 10 dans Actions et Portfolio.

## 2026-05-17
- Ajout bouton Annuler dans Orders, rafraîchissement automatique après ajout ordre.
- Correction affichage Orders : ronds de couleurs toujours visibles.

## 2026-05-16
- Création du fichier canonique de décisions UI / UX de PendleAPYito.
- Consolidation des choix déjà exprimés autour :
  - du Market Scan ;
  - des tableaux PT / LP ;
  - du formatage compact des nombres ;
  - de la lisibilité de Orders v2 ;
  - de la cohérence d'un desk manuel rapide.

## 2026-06-27
- Filtres rapides Market Scan : 4 boutons (💵 Stables only, 🚀 APY > 5%, ⏳ Maturité 30-90j, 🔄 Réinitialiser) positionnés au-dessus des filtres classiques. Reset corrigé : assignation directe au lieu de pop().
- Filtre maturité min ajouté (en plus du max existant) : `Maturité min (jours, 0 = ignore)`, step de 15 jours.
- Bouton "🌐 Refresh ALL" ajouté à côté de "Refresh markets" + "Reload cache local". Barre de progression pendant le fetch multi-chaînes. Layout 4 colonnes.
- "Chaîne à récupérer" conservée (choix A) : utile pour refresh rapide d'une seule chaîne. Le filtre d'affichage "Chaîne" en dessous reste le contrôle de tri.
- Scoring PT enrichi : bonus +15 points si spread APY implicite vs underlying ≥ 3% ("spread favorable"), malus -10 si spread ≤ -3% ("spread défavorable").
- Scoring LP intégré : TVL, volume 24h, maturité, bonus stable. Signaux 🟢 Bon LP / 🟡 LP correct / 🔴 LP faible.
- Tableau "Meilleure opportunité par actif (multi-chaînes)" ajouté en fin de Market Scan : compare les actifs présents sur plusieurs chaînes, affiche la meilleure chaîne par APY.
- KPI "Meilleur APY" : valeurs aberrantes éliminées grâce au cap APY_MAX_SANE = 1000.0 dans la normalisation.
- Blocs `st.json` (Payload préparé, Détail brut) : CSS corrigé via `_theme.py`, fond semi-transparent au lieu du carré noir opaque. Ciblage `[data-testid="stJson"]`.
- Thème AnyLiqBot appliqué globalement : deep navy + neon cyan/violet. Même thème partagé entre tous les bots. Fichier `ui/_theme.py`, appelé via `apply_theme()` dans `app.py`.
- Zéro warning Streamlit confirmé pendant la navigation après correction des conflits `value=`/`key=` sur les widgets de filtre.

## 2026-07-10 — Cockpit bar + estimation gas dans Actions

### Nouveau fichier `ui/cockpit_bar.py`
Bandeau transverse affiché dans `app.py` entre le caption et les 4 tabs (visible depuis tous les onglets).
- `render_cockpit_bar()` appelé une seule fois dans `app.py` → un seul appel kit par refresh Streamlit.
- Silencieux si aucun kit disponible (aucune erreur, aucun espace vide).

### Positionnement : `st.columns([5, 2])`
- Colonne gauche (5/7) : bandeau prix gas tokens.
- Colonne droite (2/7) : badge RPC, `justify-content: flex-end`.
- Le flexbox HTML pur n'est pas utilisé pour le positionnement gauche/droite (ne s'étend pas correctement dans le conteneur Streamlit) — st.columns fait le travail.

### Bandeau prix
- Source des chaînes : `markets.json` (chaînes effectivement fetchées, pas FETCH_CHAINS fixe).
- Format : séparateur décimal = virgule, zéro séparateur milliers (`$1737` et non `$1,737`).
- Prix < $1 : 2 décimales (`$0,09`). Prix > 100 : entier (`$1737`). Prix < $0,01 : 4 décimales (`$0,0912`).
- Mini-badges HTML `.cockpit-price` légers (sans laser trim) — le trim est réservé au badge RPC.
- Tokens sans prix CEX (MEXC/Binance) → tiret gris discret, pas d'erreur.

### Badge RPC
- Chip `.any-chip` du thème AnyLiqBot avec extension `.is-ok` : couleur = `var(--neo-blue)` (cyan, cohérent avec le reste du thème). Erreur = `.is-error` (rose).
- Taille réduite : `padding: 5px 10px`, font 12px/11px.
- Contenu : `RPC OK · {chain} · {host_masqué}`. Le numéro de bloc n'est pas affiché (trop technique). L'URL complète (clé API) n'est jamais affichée — masquage au host uniquement.
- Une seule chaîne à la fois (Option A) : la première chaîne trouvée dans `markets.json`, ou "ethereum" par défaut.

### Estimation gas dans `ui/actions.py`
- `_render_gas_hint(chain, action_type)` appelé entre `service.prepare_action()` et le bouton "Ajouter à Orders".
- `st.success` vert si `fee_usd < FEE_MAX_USD_PER_TX (0.50$)`, `st.error` rouge si dépassement.
- Le rouge n'est jamais bloquant : le clic deeplink reste toujours disponible (guardrail informatif, pas bloquant — cohérent avec l'ADR).
- Chaînes hors CHAIN_ENV_MAP (monad, plasma…) : `st.caption` discret `Gas estimé : indisponible (no_gas_price)` si fallback statique non disponible.

### Format adaptatif des montants gas (`_fmt_gas_fee`, `_fmt_token_price`)
- `_fmt_gas_fee` : adapte la précision à l'ordre de grandeur (≥ 0,01 → 4 déc. ; ≥ 0,000001 → 6 déc. ; sinon `< $0,000001`). Évite `$0,0000` pour des fees de quelques millièmes de centime.
- `_fmt_token_price` : adapte la précision du prix token (≥ 100 → entier ; ≥ 1 → 2 déc. ; ≥ 0,0001 → 4 déc.). Évite `XPL $0` pour un token à $0,09.
- `**bold**` Streamlit supprimé dans `st.success/error` (rendu en clair dans ces widgets) — texte plain avec `·` comme séparateur.
- Mention `· gwei statique` en italique si `reason == "fallback_static_gwei"`.

### Validation prod (2026-07-10)
Prix cohérents avec les trackers de marché (Ethereum Gas Tracker, prix CEX). Toutes les chaînes testées : ETH/Arbitrum/Base (RPC live), Monad/Plasma (fallback statique).

## 2026-07-12 — Refresh ALL simplifié, nouvelles chaînes dans les filtres

### Bouton "🌐 Refresh ALL" refactoré
- Remplace la boucle 8 chaînes + barre de progression par un appel unique `_refresh_all_markets_crosschain()` + `st.spinner`.
- Plus simple visuellement, plus robuste : une seule passe API cohérente, sans risque de doublons.

### Nouvelles chaînes dans les filtres
- Sonic (146), Berachain (80094) et Mantle (5000) apparaissent désormais nommées dans les filtres Market Scan et Actions (plus de numéros bruts dans les selectbox).
- Sonic et Berachain : pas encore de marchés actifs répertoriés dans PAO — présentes dans les filtres chaîne mais sans résultats associés pour l'instant.
- Mantle : display-only (pas de gas/kit configuré), marchés présents dans le scan global.

### Remarque sur FETCH_CHAINS vs Refresh ALL
- FETCH_CHAINS reste figé à 8 chaînes (Ethereum, Base, BNB, Arbitrum, Optimism, HyperEVM, Monad, Plasma). Le bouton "Refresh markets" ciblé ne couvre pas Sonic, Berachain ni Mantle.
- Le "Refresh ALL" cross-chain les récupère automatiquement sans chainId — comportement accepté, pas de besoin de refresh individuel sur ces 3 nouvelles chaînes pour l'instant.

## 2026-07-13 — Bandeau mise à jour + README distribution

### Bandeau mise à jour dans cockpit_bar.py
Affiché uniquement quand version GitHub > version locale.
Position : entre `_inject_local_styles()` et `st.columns([5, 2])` du cockpit.
Layout : `st.columns([6, 1])` — notif à gauche, bouton à droite.
- `st.info` avec lien "Voir les nouveautés" → GitHub releases/latest
- Bouton "⬇ Mettre à jour" → git pull automatique + message résultat
- Silencieux si GitHub injoignable (try/except global)

### README — section Configuration .env
Reformulée pour ne pas décourager les utilisateurs non techniques :
- RPC publics par défaut = aucune configuration obligatoire
- Alchemy = option recommandée pour usage régulier, pas prérequis
- Suppression de l'instruction "créer une app Alchemy" comme étape obligatoire

### Installation Git for Windows — 2 réglages à noter dans README
Les seuls écrans où l'utilisateur doit changer le défaut :
1. Éditeur : choisir "Use Notepad as Git's default editor"
2. git pull behavior : choisir "Fast-forward only"
Tout le reste : Next jusqu'à la fin.

## 2026-07-15 — README refondu pour distribution

### README remplacé par guide installation facile
Ancien README : orienté développeur, Alchemy obligatoire, trop technique.
Nouveau README : orienté utilisateur final, RPC publics par défaut,
Alchemy en option, procédure en 5 étapes claires.

### Section Configuration .env reformulée
- RPC publics = démarrage immédiat, aucune config obligatoire
- Alchemy = Option B, recommandé pour usage régulier uniquement
- Suppression de l'instruction "créer une app Alchemy" comme étape obligatoire

### Section Mise à jour dans README
Procédure explicite pour les amis sans PyCharm :
clic droit → "Open Git Bash here" → git pull → relancer run.bat
Mention du bouton in-app comme méthode principale.

### Guide installation Git for Windows — 2 écrans clés documentés
Captures d'écran prévues dans README pour les 2 seuls réglages à changer :
1. Éditeur : "Use Notepad as Git's default editor"
2. git pull behavior : "Fast-forward only"
Tout le reste : Next jusqu'à la fin.

### Adresse wallet dans README
Section "Soutenir le projet" ajoutée en fin de README.
Adresse wallet en bloc code pour faciliter le copier-coller.