"""
adapters/pendle_url.py

Builder de deeplinks vers l'app Pendle (app.pendle.finance).

Indépendant de transaction_kit : c'est du pur formatage d'URL, aucune
dépendance au kit. Sert à amener l'utilisateur sur le BON marché, le BON
onglet (PT / YT / LP) et la BONNE chaîne.

Limite connue : Pendle ne supporte PAS le pré-remplissage du montant via URL
(le montant est géré en state interne de l'app). On ne peut donc pré-remplir
que le marché, l'onglet et la chaîne. Le montant doit être recopié à la main
par l'utilisateur (affiché à côté du bouton côté UI).

Formats d'URL (vérifiés) :
- PT  : https://app.pendle.finance/trade/markets/{market}/swap?view=pt&chain={chain}
- YT  : https://app.pendle.finance/trade/markets/{market}/swap?view=yt&chain={chain}
- LP  : https://app.pendle.finance/trade/pools/{market}/zap/in?chain={chain}
"""

from __future__ import annotations

BASE_URL = "https://app.pendle.finance"

# ------------------------------------------------------------
# Correspondance nom de chaîne PendleAPYito -> nom attendu par Pendle
# Pendle utilise des noms spécifiques dans ses URLs (pas des chainId,
# et pas toujours le nom courant : "bnbchain" et non "bnb"/"bsc").
# ------------------------------------------------------------
CHAIN_URL_NAMES = {
    "ethereum": "ethereum",
    "base": "base",
    "arbitrum": "arbitrum",
    "optimism": "optimism",
    "bnb": "bnbchain",
    "bnbchain": "bnbchain",
    "bsc": "bnbchain",
    "hyperevm": "hyperevm",
    "hyperliquid": "hyperevm",
    "monad": "monad",
    "plasma": "plasma",
}


def _resolve_chain(chain: str | None) -> str:
    """Traduit un nom de chaîne PendleAPYito vers le nom Pendle.
    Si inconnu, renvoie la valeur telle quelle (en minuscules) en fallback."""
    if not chain:
        return "ethereum"
    key = str(chain).strip().lower()
    return CHAIN_URL_NAMES.get(key, key)


def build_pendle_url(prepared: dict) -> str | None:
    """
    Construit l'URL Pendle à partir d'un ordre PendleAPYito (dict 'prepared').

    Priorité :
    1. Si 'deposit_url' est présent dans prepared (fournie par l'API Pendle
       via marketInfo.deposit.url), on l'utilise telle quelle : c'est la
       source la plus fiable.
    2. Sinon, on construit l'URL selon action_type + market_id + chain.

    Renvoie None si on n'a pas assez d'infos (pas de market_id).
    """
    # 1. URL officielle Pendle si disponible
    deposit_url = prepared.get("deposit_url")
    if deposit_url:
        return deposit_url

    market_id = prepared.get("market_id")
    if not market_id or not str(market_id).startswith("0x"):
        return None

    chain = _resolve_chain(prepared.get("chain"))
    action = (prepared.get("action_type") or "").strip().lower()

    # 2. Construction selon le type d'action
    if "lp" in action:
        # Add LP -> zap in (structure pools, pas markets)
        return f"{BASE_URL}/trade/pools/{market_id}/zap/in?chain={chain}"

    if "yt" in action:
        return f"{BASE_URL}/trade/markets/{market_id}/swap?view=yt&chain={chain}"

    # Défaut : PT (Buy PT, et tout le reste)
    return f"{BASE_URL}/trade/markets/{market_id}/swap?view=pt&chain={chain}"


def action_supports_kit(prepared: dict) -> bool:
    """
    Indique si l'action peut passer par la validation transaction_kit.
    Pour l'instant : seul 'Buy PT' (approve + swap) est branché au kit.
    Add LP (zap) et Buy YT ne sont PAS encore validés côté kit.
    """
    action = (prepared.get("action_type") or "").strip().lower()
    return action == "buy pt"
