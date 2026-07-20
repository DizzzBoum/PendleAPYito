# PendleAPYito — system_decisions.md

## Rôle de ce fichier
Ce fichier regroupe les décisions techniques et produit déjà validées pour le projet **PendleAPYito**.  
Il sert de source de vérité afin d'éviter de rediscuter ou de déformer progressivement les choix déjà actés.

---

# 1. Identité du projet

## Nom canonique
- Le nom officiel du projet est **PendleAPYito**.
- L'ancien nom **PendleAPYitot** peut apparaître dans d'anciens échanges ou fichiers, mais il doit être considéré comme un ancien alias / une erreur historique.
- Toute nouvelle documentation, discussion ou évolution doit employer **PendleAPYito**.

## Positionnement produit
PendleAPYito est un **desk manuel Python / Streamlit** dédié à l'analyse et au pilotage d'opportunités sur Pendle.

Le projet n'est **pas** conçu, à ce stade, comme un bot d'exécution automatique.  
Son objectif actuel est de fournir un outil :
- rapide ;
- lisible ;
- utile à la décision manuelle ;
- évolutif sans brûler les étapes.

---

# 2. Architecture V1 retenue

## Structure générale
Architecture connue et validée à ce stade :
- `app.py`
- `adapters/pendle_api.py`
- `adapters/pendle_execution.py`
- `services/portfolio_service.py`
- `services/markets_service.py`
- `ui/` (market_scan.py, portfolio.py, orders.py, actions.py)
- `data/markets.json`
- `data/portfolio.json`
- `data/orders.json`

## Principe général
- **Streamlit** sert d'interface de pilotage.
- L'adapter Pendle centralise la récupération / préparation des données liées aux marchés.
- Les fichiers JSON servent de support simple pour les données locales de travail.
- La base doit rester modulaire et lisible.

## Note d'architecture (identifiée 2026-05-23)
`MarketsService` et `ui/market_scan._refresh_markets_from_api` sont deux implémentations parallèles de la même logique de fetch+normalisation. L'UI va directement vers `PendleAPI`, contournant la couche service. Acceptable pour l'instant (app mono-utilisateur) — à unifier si les deux divergent.

---

# 3. Market Scan — décisions validées

## Objectif
Le Market Scan doit permettre de repérer rapidement des marchés Pendle intéressants à partir de critères pertinents.

## Informations clés suivies
- APY / implied APY
- TVL
- maturité
- durée restante jusqu'à maturité
- chaîne
- activité du marché
- familles PT / LP quand pertinent

## Décisions déjà validées
- Conversion robuste des colonnes numériques via `pd.to_numeric`.
- Gestion propre des valeurs manquantes / conversions problématiques.
- Filtres fonctionnels sur :
  - `implied_apy`
  - `tvl_usd`
  - `days_to_maturity`
- Filtre `only_active` conservé.
- Les incohérences de type et les cas "aucun résultat" liés à des filtres trop restrictifs doivent être traités de façon lisible.

## Multi-chaînes
- Selectbox "Chaîne à récupérer" ajoutée avec support pour : Ethereum, Base, BNB, Arbitrum, Optimism, HyperEVM.
- L'API Pendle accepte un paramètre `chain_id` optionnel pour filtrer côté serveur.
- Chaînes prioritaires en production : Base, BNB, HyperEVM, Arbitrum (frais bas).

---

# 4. PT / LP — décisions produit

## Orientation
PendleAPYito doit aider à comparer et suivre des opportunités de type :
- **PT**
- **LP**

## État validé
- Des tableaux PT et LP existent déjà dans l'interface.
- Leur lecture doit rester claire et directement exploitable.
- Les données doivent rester cohérentes avec le Market Scan et les filtres disponibles.

---

# 5. Orders v2 — état actuel

## Statut
Orders v2 est **stable et fonctionnel**.

## Décisions déjà prises
- Les ordres sont structurés sous forme de **dictionnaires**.
- Le statut initial utilisé est :
  - `OPEN`
- La date de création utilise :
  - `datetime.now(timezone.utc).isoformat()`
- Les IDs suivent un format de type :
  - `ord_###`

## Corrections appliquées
- Génération ID ordres corrigée : `max(existing_ids) + 1` au lieu de `len(orders) + 1` pour éviter doublons après suppression.
- Colonne "Âge" ajoutée : affiche `2m`, `5h`, `12j`, avec alerte visuelle `⚠️ Xj` si > 3 jours.
- Bouton "Supprimer les ordres > 3 jours" qui apparaît automatiquement si ordres anciens détectés.
- Ronds de couleurs : 🟢 OPEN, 🟡 SIMULATED, 🔴 CANCELLED (toujours affichés, même dans les détails).
- Tableau résumé en haut de page avec toutes les infos clés.
- **Bug timezone corrigé (2026-05-23)** : `datetime.now()` → `datetime.now(timezone.utc)` dans `ui/orders.py:22` pour éviter des âges incorrects hors UTC.

## Intention fonctionnelle
Orders v2 doit tendre vers un suivi manuel simple et fiable :
- préparer des ordres ;
- les afficher proprement ;
- les persister ;
- permettre ensuite les évolutions utiles au suivi, sans basculer prématurément dans un système d'exécution automatique.

---

# 6. Portfolio — état actuel

## Mode lecture wallet (Option 1)
- Champ "Adresse wallet" ajouté dans l'UI Portfolio.
- Si adresse fournie → tentative de fetch depuis API Pendle.
- Si vide ou erreur → fallback sur mock.

## Problème identifié
- Endpoint testé `/v1/users/{address}/all-positions` → **404 Not Found**.
- L'endpoint correct pour récupérer les positions utilisateur n'est pas documenté publiquement dans l'API Pendle v2.
- Recherches effectuées dans la doc officielle et via web search sans succès.

## Solution retenue
- **Garder le mock Portfolio pour l'instant**.
- Priorité : développer l'exécution d'ordres via SDK Pendle.
- Une fois l'exécution fonctionnelle, on pourra revenir sur la lecture automatique des positions (via blockchain direct, API tierce, ou endpoint trouvé).

## Actions rapides
- Section "Actions rapides" dans Portfolio : permet de créer un ordre depuis une position existante.
- Dropdown positions + formulaire (type action + montant) + bouton "Créer l'ordre".
- Ordre sauvegardé dans orders.json avec rafraîchissement automatique.

---

# 7. Multi-stablecoins — décision validée (2026-05-23)

## Contexte
Le projet ne supportait que USDC. Support étendu à tous les stablecoins USD majeurs.

## Décision
- `USDC_BY_CHAIN` remplacé par `TOKEN_ADDRESSES_BY_CHAIN` dans `adapters/pendle_execution.py`.
- Stablecoins supportés : **USDC, USDT, DAI, USDe, FRAX**.
- Chaînes couvertes : Ethereum, Base, BNB, Arbitrum, Optimism, HyperEVM.
- Le champ `stable_token` est ajouté aux ordres (défaut : `"USDC"` pour rétrocompatibilité).
- `prepare_from_order` utilise le token address correspondant au `stable_token` de l'ordre.
- Note : `token_in_decimals=6` est conservé dans `_normalize_response` — n'affecte que l'affichage, pas le calcul wei on-chain (correct via `amount_stable_wei` dans `prepare_from_order`).

## Chaînes prioritaires
Base, BNB Chain, HyperEVM (frais bas). Ethereum en priorité basse.

---

# 8. Deeplinks Pendle.finance — montant dans l'URL

## État actuel (2026-05-23)
- Méthode `_build_pendle_url` modifiée dans `adapters/pendle_execution.py`.
- Le paramètre `inputAmount` est maintenant ajouté aux branches LP et fallback (la branche PT était déjà correcte).
- `orders.py` transmet déjà `amount_display=str(amount)` pour tous les types d'action.

## Problème ouvert
- Pendle ne reconnaît pas le paramètre `inputAmount` et ne pré-remplit pas le champ montant.
- Le nom exact du paramètre URL attendu par Pendle n'est pas documenté publiquement.
- **Sujet mis en attente** — à reprendre quand le bon paramètre sera identifié.

---

# 9. Bugs identifiés et non encore corrigés

## MarketsService cassé
- Fichier : `services/markets_service.py:13`
- `PendleAPI.__init__` n'a pas de valeur par défaut pour `base_url` → crash à l'instanciation.
- Sans impact immédiat (UI contourne le service), mais code mort à corriger.

## Adresse USDC HyperEVM manquante
- Fichier : `adapters/pendle_execution.py`
- `TOKEN_ADDRESSES_BY_CHAIN` n'a pas encore d'entrée complète pour HyperEVM (chain 999).
- Fallback silencieux sur l'adresse Ethereum — à corriger avec la vraie adresse USDC HyperEVM.

## Méthode privée appelée depuis l'UI
- Fichier : `ui/orders.py:284`
- `adapter._build_pendle_url(...)` appelé directement depuis l'UI.
- Convention à corriger : rendre la méthode publique ou exposer un wrapper.

---

# 10. Ce qui n'est pas le chantier actuel

## Pas d'automatisation on-chain immédiate
PendleAPYito ne doit pas être transformé maintenant en bot de transactions automatiques.  
Une automatisation future est possible, mais elle ne doit pas détourner la version actuelle de son rôle de desk manuel.

## Moteur d'exécution futur
Une future version pourra s'appuyer sur un moteur d'exécution commun sécurisé, également envisagé pour AnyLiqBot et d'autres bots.  
Ce sujet est à garder en mémoire, mais **ne doit pas être ouvert automatiquement**.

---

# 11. Pistes stratégiques futures à garder en mémoire

## YT / PT plus élaborés
Une piste future importante concerne des stratégies plus avancées autour :
- du timing d'achat / vente des **YT** ;
- de l'effet de levier potentiel des YT ;
- de stratégies proches d'un **delta-neutral simplifié**.

## Documentation future possible
Un fichier markdown explicatif dédié pourra être créé plus tard pour poser proprement :
- les intuitions ;
- les risques ;
- les scénarios de stratégie ;
- les contraintes techniques.

---

# 12. Montants par défaut

## Décision validée
- Montants par défaut réduits à **10** (au lieu de 100 ou 1000) pour faciliter les tests sans risque.
- Fichiers concernés : `ui/actions.py` et `ui/portfolio.py`.

---

# 13. Règles de travail pour les futures évolutions

- Avancer par petites étapes validées.
- Ne pas refondre l'architecture sans raison forte.
- Ne pas confondre objectif V1 manuel et automatisation future.
- En cas de doute sur l'état réel du code, vérifier les fichiers source actuels avant d'affirmer.
- Les décisions stabilisées présentes dans ce fichier servent de référence prioritaire.

---

# History

## 2026-06-30 — Piste future notée : passage V0 → V1 (exécution réelle)

- **Statut : REPORTÉ — noté comme cap, non lancé.** Aucun travail en cours.
- L'architecture transaction_kit est déjà prête structurellement pour l'exécution réelle. La propriété `is_executable` du TransactionPlan trace le chemin : `mode == EXECUTE` + `status == CONFIRMED` + zéro erreur de validation + `checklist_signature` présente.
- Pour activer un jour l'exécution réelle depuis PendleAPYito, il faudrait (côté kit, avec ADR + tests dédiés) :
  - un nouveau `safety_profile` `v1_guarded_execute` (déjà esquissé en commentaire dans `SAFETY_PROFILES`) autorisant le mode `execute` ;
  - un `signer` réel passé à `execute()` (implique clés privées / gas / RPC privé — cf ADR-016 Alchemy du kit) ;
  - le passage explicite en `mode=EXECUTE`, qui reste bloqué en V0 par les gates ADR-002.
- Côté PendleAPYito, cela signifierait réactiver `confirm_and_execute` dans `txkit_bridge.py` (fonctions conservées, actuellement non exposées dans l'UI) et rebrancher un flux de confirmation dans l'onglet Actions.
- **Ne pas lancer sans demande explicite.** C'est le chantier V0→V1, ambitieux (sécurité fonds réels), à traiter comme projet dédié dans transaction_kit d'abord. PendleAPYito reste un desk manuel : deeplink + validateur en V0.


## 2026-06-30
- **Branchement transaction_kit (validateur, dry-run)** : adaptateur-pont optionnel `adapters/txkit_bridge.py` créé, import protégé (`KIT_AVAILABLE`). Le cockpit fonctionne sans le kit. Flux "Buy PT" = approve (exact_amount) + swap via Router V4, traduit depuis le dict `prepared`. `contract` = Router V4 partout, `market_id` PendleAPYito → `params.market`.
- **Installation kit** : `pip install -e ../transak_kit` validé, `pyproject.toml` créé pour le package `transaction_kit`.
- **Allowlisting des PT abandonné** : les tokens PT/SY/LP Pendle sont des contrats générés par Pendle, uniques par marché/maturité, sans référence vérifiable sur Blockscout. La sécurité porte sur le token d'entrée (stables allowlistés) + Router V4 vérifié, pas sur le token de sortie. Seuls les marchés à token connu (ex: wstETH) passent la validation kit ; c'est voulu.
- **Orientation "validateur de deeplink"** : transaction_kit ne sert PAS d'exécuteur dans PendleAPYito mais de validateur des paramètres d'entrée. L'exécution réelle se fait manuellement sur app.pendle.finance via deeplink. Pendle ne pré-remplit pas le montant via URL (state interne) → le montant est affiché à recopier.
- **Builder de deeplink** : `adapters/pendle_url.py` créé (indépendant du kit). Construit les URLs Pendle pour 3 cas : PT (`/trade/markets/{m}/swap?view=pt&chain=`), YT (`view=yt`), LP (`/trade/pools/{m}/zap/in?chain=`). Table de correspondance des noms de chaîne Pendle (bnb→bnbchain, hyperliquid→hyperevm, + monad, plasma). Priorité au `deposit_url` officiel si présent. Validation kit seulement pour Buy PT ; LP/YT en deeplink direct.
- **Chaînes Monad et Plasma ajoutées** : `FETCH_CHAINS` (Monad=143, Plasma=9745) et `chain_map` (143→monad, 9745→plasma) dans `market_scan.py`. Pendle a des marchés actifs sur ces deux chaînes (confirmé : syzUSD, sUSDe sur Plasma).
- **Imperfection connue (côté kit, hors PendleAPYito)** : le "Total USD estimé" additionne approve+swap. À corriger dans transaction_kit (ignorer les steps approve), avec test + ADR dédié.
- **À purger** : doublons `143`/`9745` vs `monad`/`plasma` dans `markets.json` (anciennes entrées normalisées avant patch). Supprimer `data/markets.json` + Refresh ALL pour nettoyer.

## 2026-06-28
- **Enrichissement normalizer** : `_normalize_markets()` extrait désormais `lp_max_boosted_apy` (depuis `details.maxBoostedApy`, même garde-fou APY_MAX_SANE), `points` (multiplicateurs/airdrops formatés depuis `points[]`, ex "USD.AI ×12"), et les champs `marketInfo` pour la fiche détail : `info_description`, `info_risk`, `info_quirks` (quirks génériques masqués), `info_conversion`, `info_protocols`, `info_deposit_url`. HTML nettoyé via `_strip_html`.
- **ROI PT/YT abandonné** : `pt_roi`/`yt_roi` avaient été ajoutés puis retirés complètement (normalizer + affichage). Raison : le ROI Pendle est un rendement brut sur la période (non annualisé), il récompenserait mécaniquement les longues maturités s'il entrait dans le scoring. L'APY reste le seul moteur des scores PT/LP. Le sujet leviers/ROI sera traité dans le futur chantier YT.
- **Scoring inchangé** : `_score_pt_row` et `_score_lp_row` restent basés uniquement sur APY, maturité, TVL, spread, bonus stable. Aucune pondération ROI.
- **Source snapshot** : `data/markets_raw.json` ajouté comme référence debug (réponse API brute avant normalisation). `data/markets.json` reste le fichier principal exploité par l'UI. Snapshot analysé : 46 marchés HyperEVM, 38/46 avec points, 45/46 avec riskInvolved, 46/46 avec conversionRate.
- **Filtre chaîne Actions** : `ui/actions.py` dispose d'un selectbox "Chaîne" propre (ALL + chaînes disponibles), indépendant du filtre Market Scan (choix B). Placé avant le tri APY et le choix du marché.
 
## 2026-06-20
- Suppression de FRAX du support multi-stablecoins (plus utile, simplification).
- `TOKEN_ADDRESSES_BY_CHAIN` nettoyé sur les 5 chaînes concernées : Ethereum, BNB, Arbitrum, Optimism, Polygon.
- `STABLE_DECIMALS` nettoyé en conséquence.
- HyperEVM (chain 999) conservé tel quel (`{}`) — reste visible dans Market Scan, sans stablecoin d'exécution configuré pour l'instant.
- USDH (stablecoin Hyperliquid) évoqué mais non implémenté — jugé non indispensable pour l'instant.
- `ui/actions.py` : aucune modification nécessaire, le sélecteur "Token d'entrée" est dynamique via `get_available_stables()` et reflète automatiquement la liste à jour.
- Stablecoins supportés désormais : USDC, USDT, DAI, USDe.

## 2026-05-23 — Session Claude Code CLI (v2.1.148)
Première session de travail avec **Claude Code CLI** sur le projet PendleAPYito.
- Analyse complète du projet par Claude Code : architecture confirmée, 4 bugs identifiés.
- **Bug timezone corrigé** : `datetime.now()` → `datetime.now(timezone.utc)` dans `ui/orders.py:22`.
- **Multi-stablecoins** : `USDC_BY_CHAIN` → `TOKEN_ADDRESSES_BY_CHAIN` avec USDC, USDT, DAI, USDe, FRAX sur toutes les chaînes. Champ `stable_token` ajouté aux ordres.
- **Deeplinks** : `inputAmount` ajouté dans `_build_pendle_url` (branches LP et fallback). Problème ouvert : Pendle ne reconnaît pas ce paramètre.
- Bugs restants documentés : MarketsService cassé, adresse USDC HyperEVM manquante, méthode privée appelée depuis UI.

## 2026-05-20
- Adapter `pendle_execution.py` créé : prépare les transactions via API SDK Pendle.
- Méthodes : Buy PT, Sell PT, Add LP, Remove LP, prepare_from_order.
- Helpers : _get_market_metadata, _format_amount, _build_pendle_url.
- Slippage configurable (défaut 1%, jusqu'à 20% pour tokens peu liquides).
- Décision : API SDK Pendle trop instable (400/404, parsing incomplet) → bouton simplifié en lien direct Pendle.finance.
- Bouton "Préparer" remplacé par st.link_button → ouvre Pendle.finance sur le bon market + chain.
- Chantiers futurs priorisés : Stabilisation > Market Scan > Alertes > Portfolio > YT.
- 
## 2026-05-19
- Orders v2 finalisé : colonne Âge, nettoyage automatique, ronds de couleurs toujours visibles.
- Portfolio : champ adresse wallet ajouté, Actions rapides fonctionnelles.
- Market Scan : support multi-chaînes avec selectbox.
- Recherche endpoint API Pendle pour positions utilisateur : échec (404 sur `/v1/users/{address}/all-positions`).
- Décision : garder mock Portfolio, focus sur exécution ordres via SDK Pendle.
- Montants par défaut réduits à 10 pour tests.

## 2026-05-17
- Corrections initiales groupées : nom projet, checkbox key unique, génération ID ordres.
- Market Scan : ajout chain_map, fonction `_refresh_markets_from_api(chain_id)`.
- Orders v2 : boutons Annuler et Simuler conditionnels.

## 2026-05-16
- Création du fichier de décisions techniques canonique de PendleAPYito.
- Nom officiel figé : **PendleAPYito**.
- Consolidation des décisions connues autour de :
  - l'architecture V1 ;
  - Market Scan ;
  - PT / LP ;
  - Orders v2 ;
  - les sujets futurs à conserver sans les lancer immédiatement.

## 2026-06-27
- **Crash ValueError corrigé** : garde-fou ajouté dans `ui/market_scan.py` — si `filtered` est vide après filtrage, `return` propre avant le scoring PT/LP (évite le `Length mismatch: Expected axis has 12 elements, new values have 3 elements`).
- **Reset filtres corrigé** : bouton "Réinitialiser" dans Market Scan remplacé de `session_state.pop()` vers assignation directe des valeurs par défaut. Fonctionne maintenant sans conflit Streamlit.
- **PT expirés exclus** : filtre explicite `days_to_maturity >= 0` ajouté dans la section filtrage de Market Scan, indépendant du champ `is_active` du cache (qui pouvait être périmé).
- **Tri Actions par APY** : `available_markets` trié par `implied_apy` décroissant avant construction des labels dans `ui/actions.py`. Le meilleur marché apparaît en premier dans le selectbox.
- **Multi-chaînes global** : `_save_markets()` modifiée avec paramètre `merge=True` — fusionne les marchés au lieu d'écraser le cache. Bouton "🌐 Refresh ALL" ajouté, boucle sur toutes les chaînes avec barre de progression. La sélection "Chaîne à récupérer" + "Refresh markets" conservée pour refresh rapide d'une seule chaîne (choix A validé).
- **APY sanity cap** : garde-fou `APY_MAX_SANE = 1000.0` ajouté dans `_normalize_markets()`. Les APY > 1000% ou négatifs sont mis à `None`. Corrige le KPI "Meilleur APY" qui affichait des valeurs aberrantes (858 trillions %).
- **Warning Streamlit éliminé** : conflit `value=` + `key=` sur les widgets de filtre résolu. Initialisation des défauts via `setdefault` en début de `render_market_scan()`, suppression des `value=`/`index=` sur les widgets filtrés. Zéro warning confirmé en navigation.
- **Thème AnyLiqBot appliqué** : `ui/_theme.py` copié depuis AnyLiqBot, `apply_theme()` appelé dans `app.py` après `set_page_config()`. CSS patch ajouté ciblant `[data-testid="stJson"]` pour fond semi-transparent sur les blocs JSON (au lieu du carré noir opaque par défaut).
- **Position simulée** confirmée comme comportement normal : le statut `SIMULATED` est un marqueur d'état manuel, aucune transaction ne tourne en arrière-plan.
- **Wallet portfolio** : détection zéro positions confirmée comme problème connu (endpoint API `/v1/users/{address}/all-positions` → 404). Reste sur mock, déféré au chantier Portfolio enrichi (priorité 4).


## 2026-07-10 — Intégration des 3 kits defi dans le cockpit (lecture seule)

### Nouveau fichier `adapters/kits_bridge.py`
Passerelle centralisée vers `defi_price_kit`, `defi_fee_kit`, `defi_rpc_kit`.
- Imports conditionnels `HAS_PRICE_KIT` / `HAS_FEE_KIT` / `HAS_RPC_KIT` : le cockpit tourne sans les kits.
- Python pur, zéro import streamlit : utilisable hors UI.
- Coexiste avec `adapters/txkit_bridge.py` (qui gère `transaction_kit` / validation dry-run) sans chevauchement.

### defi_price_kit — branché
- Singleton `_price_provider = PriceProvider.from_env()`.
- `get_prices_for_chains(chains)` : retourne `{gas_token: prix_usd}` pour les chaînes présentes dans `markets.json`.
- Mapping `CHAIN_GAS_TOKEN` : ethereum/optimism/arbitrum/base → ETH, bnb/bsc → BNB, polygon → POL, hyperevm/hyperliquid → HYPE, monad → MON, plasma → XPL. MNT (Mantle) supprimé — chaîne retirée du projet.

### defi_rpc_kit — branché
- Signatures confirmées sur le code source réel (2026-07-07) :
  - `RpcProvider.from_env(chain: str)` — chain en string lowercase.
  - `provider.gas_price()` → int (wei, passthrough brut).
  - `provider.health()` → `{chain, connected, block_number, provider_url, timeout_sec, profile}`.
- **Singleton par chaîne** : `_rpc_providers: Dict[str, RpcProvider] = {}` — `from_env(chain)` prend la chain à la construction, d'où un cache par chaîne (pattern différent du price_provider unique).
- Chaînes ETH / Arbitrum / Base : RPC live Alchemy, gas_price réel.
- Chaînes Monad / Plasma / Hyperliquid / BNB : hors `CHAIN_ENV_MAP` du kit → fallback statique gwei (voir ci-dessous). Long-terme : enrichir `CHAIN_ENV_MAP` côté `defi_rpc_kit`.

### `estimate_gas_indicative(chain, action_type)` — nouvelle fonction publique
Calcul indicatif pour mode deeplink (ne nécessite aucun tx dict, indépendant du fee_kit) :
`gas_units × gas_price_wei × gas_token_price_usd / 1e18`
- Gas units Pendle Router V4 : Buy PT = 250k, Add LP = 350k, Remove LP = 280k, Claim rewards = 150k.
- Retourne un dict stable `{available, gas_units, gas_price_gwei, gas_token, gas_token_price_usd, fee_native, fee_usd, max_usd, exceeds_max, reason}`.
- Ordre de grandeur, pas une estimation exacte — le fee_kit officiel (`estimate_gas()`) reste câblé pour V1 exécution réelle.

### Fallback statique gwei (chaînes hors CHAIN_ENV_MAP)
Quand `gas_price_wei` est None (provider non configuré), fallback statique activé :
MON = 0.5 gwei, XPL = 0.5 gwei, BNB = 1.0 gwei, HYPE = 0.5 gwei.
Le dict retourné porte `reason: "fallback_static_gwei"` — distinguable d'une mesure live.
Validé en prod : prix cohérents avec les trackers de marché.

### `rpc_health(chain)` — nouvelle fonction publique
Retourne `{available, ok, chain, block_number, provider_url, reason}`.
`provider_url` jamais affiché tel quel dans l'UI — masqué au host via `_mask_provider_url()` (clé API Alchemy non exposée).

### defi_fee_kit — câblé, bloqué en V0
`estimate_gas()` retourne `available=False` / `reason="no_tx_in_deeplink_mode"`. Volontaire : le mode deeplink ne construit pas de tx dict. Câblé pour V1 (TODO commenté dans la zone signatures).

### Bug résolu : import circulaire
Snippet de diagnostic (`from adapters.kits_bridge import ...`) avait été accidentellement collé dans `kits_bridge.py` lui-même (~ligne 28) → crash au démarrage. Fix : supprimer ces 3 lignes. Le snippet de test doit être lancé dans un terminal Python séparé, depuis la racine du projet.

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

## 2026-07-13 — Distribution GitHub + système de mise à jour

### Repo GitHub créé
- URL publique : https://github.com/DizzzBoum/PendleAPYito
- Premier commit : b4c5f90 — 28 fichiers, PAO v0.1.0
- Release GitHub publiée : v0.1.0 "PAO v0.1.0 — Premier release public"
- Tag : v0.1.0, branche : main, label : Latest

### Fichiers de distribution créés (Claude Code)
- `.gitignore` : exclut .env, .venv/, __pycache__/, data/*.json, tx_logs/,
  .idea/, *.py~, .claude/, ANALYSE_*.md
- `data/.gitkeep` : placeholder pour dossier data/ dans le repo
- `.env.example` : template complet avec RPC publics pré-remplis + couleurs thème
- `version.py` : `__version__ = "0.1.0"`, `__app_name__ = "PendleAPYito"`
- `first_run.bat` : installation Windows (vérifie Python + Git, crée venv,
  pip install, copie .env.example → .env)
- `run.bat` : lancement Windows (active venv, streamlit run app.py)
- `README.md` : documentation utilisateur en français

### requirements.txt corrigé
- Ré-encodé UTF-16 → UTF-8 (aurait fait échouer pip install chez les amis)
- 4 lignes `-e c:\users\nom_utilisateur\...` commentées (chemins locaux non portables)
- Les kits defi (defi_price_kit, defi_rpc_kit, defi_fee_kit, transaction_kit)
  ne sont PAS sur PyPI — installés localement via pip install -e uniquement
  sur la machine du mainteneur. Sans eux, PAO fonctionne en mode dégradé
  (pas de bandeau prix, pas de gas estimé) — comportement voulu, silencieux.

### RPC publics dans .env.example
Endpoints publics gratuits pré-remplis — aucune configuration obligatoire
pour démarrer PAO :
- RPC_ETHEREUM=https://eth.llamarpc.com
- RPC_ARBITRUM=https://arb1.arbitrum.io/rpc
- RPC_BASE=https://mainnet.base.org
- RPC_OPT=https://mainnet.optimism.io
- RPC_BNB=https://bsc-dataseed.binance.org/
- RPC_MONAD=https://rpc.monad.xyz
- RPC_PLASMA=https://rpc.plasma.io
- RPC_HYPERLIQUID=https://rpc.hyperliquid.xyz/evm
Alchemy reste recommandé pour fiabilité — optionnel, documenté dans README.

### Système de mise à jour in-app (cockpit_bar.py)
- `_check_latest_version()` : appel `api.github.com/repos/DizzzBoum/PendleAPYito/releases/latest`
  caché 1h (`@st.cache_data(ttl=3600)`)
- Bandeau `st.info` si version distante > `__version__` local
- Bouton "⬇ Mettre à jour" : `subprocess.run(["git", "pull"])` depuis la racine du projet
- Silencieux si GitHub injoignable ou `version.py` absent
- Fonctionne uniquement si le projet a été installé via `git clone`
  (pas via zip)

### Workflow de publication d'une nouvelle version
1. Modifier `version.py` → incrémenter `__version__`
2. `git add . && git commit -m "feat: ..." && git push`
3. GitHub → Releases → Draft new release → tag vX.Y.Z → Publish
4. Le bandeau apparaît automatiquement chez les utilisateurs

### Monétisation — décision
- Referral Pendle : inexistant (confirmé doc officielle + recherche)
- Fee sur transactions : impossible en V0 deeplink, complexe et réglementé en V1
- Solution retenue : tip volontaire (adresse wallet + Ko-fi dans README)
  Non implémenté dans l'UI pour l'instant

## 2026-07-15 — Distribution amis + corrections post-release

### requirements.txt — corruption UTF-16 résolue
Fichier corrompu (NUL bytes) suite à double conversion d'encodage par Claude Code.
Résolution : pip freeze > requirements_new.txt depuis le venv, suppression manuelle
des 6 lignes -e locales (defi_fee_kit, defi_price_kit, defi_rpc_kit), renommage.
Règle établie : toujours régénérer via pip freeze en cas de doute sur l'encodage.
Les 3 kits defi ne sont PAS dans requirements.txt — non distribuables publiquement.
PAO fonctionne en mode dégradé sans eux (silencieux via HAS_PRICE_KIT etc.).

### Conflit Git résolu (fast-forward divergence)
Cause : README modifié directement sur GitHub + commits locaux simultanés.
Résolution : git fetch origin → git reset --soft origin/main → git push.
Note : "Fast-forward only" configuré lors de l'install Git bloque les merges
automatiques — préférer modifier les fichiers en local puis pusher plutôt
que d'éditer directement sur GitHub.

### Endpoints RPC publics validés
Pré-remplis dans .env.example — aucune configuration obligatoire pour démarrer :
RPC_ETHEREUM=https://eth.llamarpc.com
RPC_ARBITRUM=https://arb1.arbitrum.io/rpc
RPC_BASE=https://mainnet.base.org
RPC_OPT=https://mainnet.optimism.io
RPC_BNB=https://bsc-dataseed.binance.org/
RPC_MONAD=https://rpc.monad.xyz
RPC_PLASMA=https://rpc.plasma.io
RPC_HYPERLIQUID=https://rpc.hyperliquid.xyz/evm
Alchemy reste recommandé pour fiabilité — optionnel, documenté dans README.

### Bug installation premier utilisateur
Streamlit non installé chez le premier ami testeur.
Cause : requirements.txt corrompu → pip install silencieusement incomplet.
Fix immédiat : .venv\Scripts\pip install streamlit dans CMD.
Fix permanent : requirements.txt régénéré proprement et pushé.

### Procédure mise à jour pour les amis (sans PyCharm)
Deux méthodes selon le contexte :
1. Bouton "⬇ Mettre à jour" dans PAO (git pull automatique) — recommandé
2. Clic droit dans le dossier PendleAPYito → "Open Git Bash here" → git pull
→ relancer run.bat dans les deux cas.
Pas besoin de compte GitHub pour git pull sur repo public.

### Monétisation — adresse wallet ajoutée au README
Adresse : 0x9602Ac4E681D11Ff5dcA4a076BfeEFBb09e2fFbD
Réseaux : Ethereum, Base, Arbitrum.
Tout token ERC-20 accepté. Pas de programme referral Pendle (inexistant).