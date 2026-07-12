"""
adapters/kits_bridge.py

Passerelle centralisée vers les kits communs (defi_price_kit, defi_fee_kit,
defi_rpc_kit) livrés depuis transak_kit.

Objectif : brancher les kits en LECTURE SEULE sur le cockpit Streamlit,
sans jamais casser l'app si un kit est absent.

État actuel :
- defi_price_kit : BRANCHÉ (bandeau prix temps réel)
- defi_fee_kit   : CÂBLÉ mais BLOQUÉ en V0 deeplink (besoin d'un tx dict
                    que le mode deeplink ne construit pas). Prêt pour V1.
- defi_rpc_kit   : BRANCHÉ pour estimation gas indicative + santé RPC.

Principes :
- Aucune exécution réelle, aucun broadcast, aucune clé privée ici.
- Les appels kit sont isolés dans la "ZONE SIGNATURES KITS" —
  le seul endroit à ajuster si l'API réelle change.
- Le module reste en Python pur (pas d'import streamlit).
"""


from __future__ import annotations

import os
from typing import Optional, Dict, List, Any


# ============================================================
# Détection des kits (imports conditionnels)
# ============================================================

try:
    #from __future__ import annotations
    from defi_price_kit import PriceProvider
    HAS_PRICE_KIT = True
except Exception:
    PriceProvider = None  # type: ignore[assignment,misc]
    HAS_PRICE_KIT = False

try:
    from defi_fee_kit import FeePolicy
    HAS_FEE_KIT = True
except Exception:
    FeePolicy = None  # type: ignore[assignment,misc]
    HAS_FEE_KIT = False

try:
    from defi_rpc_kit import RpcProvider
    HAS_RPC_KIT = True
except Exception:
    RpcProvider = None  # type: ignore[assignment,misc]
    HAS_RPC_KIT = False

# Flag combiné : True si les 3 kits nécessaires aux fonctionnalités
# complètes (prix + gas + rpc) sont tous présents.
DEFI_KITS_AVAILABLE = HAS_PRICE_KIT and HAS_FEE_KIT and HAS_RPC_KIT

# Garde-fou gas (ADR transaction_kit : FEE_MAX_USD_PER_TX=0.50).
FEE_MAX_USD_PER_TX = float(os.getenv("FEE_MAX_USD_PER_TX", "0.50"))


# ============================================================
# Mapping chaîne -> gas token natif
# ============================================================
# Seuls les coins servant à payer les frais (gas token natif).
# ARB volontairement exclu : token de gouvernance, pas gas token
# (Arbitrum se paie en ETH).

CHAIN_GAS_TOKEN: Dict[str, str] = {
    "ethereum":    "ETH",
    "arbitrum":    "ETH",
    "base":        "ETH",
    "optimism":    "ETH",
    "bnb":         "BNB",
    "bsc":         "BNB",
    "monad":       "MON",
    "plasma":      "XPL",
    "hyperevm":    "HYPE",
    "hyperliquid": "HYPE",
    "sonic":       "S",
    "berachain":   "BERA",
}

# Mapping gas token -> paire CEX pour defi_price_kit (format MEXC/Binance).
# Le kit attend le symbole CEX complet, pas juste le ticker.
# Si un token n'existe pas sur MEXC/Binance, get_price retournera None.
_GAS_TOKEN_TO_CEX_PAIR: Dict[str, str] = {
    "ETH":  "ETHUSDT",
    "BNB":  "BNBUSDT",
    "HYPE": "HYPEUSDT",
    "MON":  "MONUSDT",
    "XPL":  "XPLUSDT",
    "POL":  "POLUSDT",
    "S":    "SUSDT",
    "BERA": "BERAUSDT",
}

# Consommation gas indicative par type d'action Pendle (Router V4).
# Valeurs ajustées pour Pendle spécifiquement — swaps Router V4 plus lourds
# qu'un swap Uniswap simple. Utilisé uniquement en mode deeplink pour donner
# un ordre de grandeur ; en V1 exécution réelle, le fee_kit fera l'estimation
# précise à partir du tx dict.
_ACTION_GAS_UNITS: Dict[str, int] = {
    "Buy PT":        250_000,   # approve (~46k) + swap Router V4 (~200k)
    "Sell PT":       250_000,   # approve + swap Router V4
    "Add LP":        350_000,   # approve + add liquidity multi-token
    "Remove LP":     280_000,   # zap out, un peu plus léger qu'Add LP
    "Claim rewards": 150_000,   # claim multi-reward tokens possible
}
_DEFAULT_GAS_UNITS = 250_000


def gas_token_for_chain(chain: Optional[str]) -> Optional[str]:
    """Retourne le symbole du coin natif (gas) pour une chaîne, ou None."""
    if not chain:
        return None
    return CHAIN_GAS_TOKEN.get(chain.strip().lower())


def gas_tokens_for_chains(chains: List[str]) -> List[str]:
    """Liste dédupliquée des gas tokens pour un ensemble de chaînes.

    ETH en premier (chaîne la plus fréquente), puis alphabétique.
    """
    seen: list[str] = []
    for c in chains:
        sym = gas_token_for_chain(c)
        if sym and sym not in seen:
            seen.append(sym)
    ordered = (["ETH"] if "ETH" in seen else []) + sorted(
        s for s in seen if s != "ETH"
    )
    return ordered


def action_gas_units(action_type: Optional[str]) -> int:
    """Consommation gas indicative pour un type d'action Pendle."""
    if not action_type:
        return _DEFAULT_GAS_UNITS
    return _ACTION_GAS_UNITS.get(action_type, _DEFAULT_GAS_UNITS)


# ============================================================
# Singletons providers
# ============================================================
# PriceProvider : instance unique.
# RpcProvider   : une instance PAR CHAÎNE (le kit prend la chain à la
#                 construction via from_env(chain)), dict lazy.

# new_str
_price_provider = None
_rpc_providers: Dict[str, "RpcProvider"] = {}


def _get_price_provider():
    """Lazy singleton pour PriceProvider. None si kit absent."""
    global _price_provider
    if not HAS_PRICE_KIT:
        return None
    if _price_provider is None:
        try:
            _price_provider = PriceProvider.from_env()
        except Exception:
            return None
    return _price_provider


def _get_rpc_provider(chain: str) -> Optional["RpcProvider"]:
    """Lazy singleton PAR CHAÎNE pour RpcProvider. None si kit absent.

    RpcProvider prend la chain à la construction (`from_env(chain)`),
    d'où le cache {chain_normalisée: instance}. Le kit gère lui-même
    les alias (eth→ethereum, arb→arbitrum) ; on normalise juste en lowercase.
    """
    if not HAS_RPC_KIT:
        return None
    chain = chain.strip().lower()
    if chain not in _rpc_providers:
        try:
            _rpc_providers[chain] = RpcProvider.from_env(chain)
        except Exception:
            return None
    return _rpc_providers[chain]




# ============================================================
# ZONE SIGNATURES KITS - PRICE
# ------------------------------------------------------------
# Signatures vérifiées le 2026-07-07 via le projet transak_kit.
# ============================================================

def _kit_fetch_price_usd(symbol: str) -> Optional[float]:
    """Appelle defi_price_kit.PriceProvider.get_price(pair_cex)."""
    provider = _get_price_provider()
    if provider is None:
        return None

    cex_pair = _GAS_TOKEN_TO_CEX_PAIR.get(symbol)
    if not cex_pair:
        return None

    try:
        result = provider.get_price(cex_pair)
        # result attendu : {"ok": True, "source": "mexc", "price": 2145.30, ...}
        if isinstance(result, dict) and result.get("ok"):
            return float(result["price"])
        return None
    except Exception:
        return None


# ============================================================
# ZONE SIGNATURES KITS - FEE
# ------------------------------------------------------------
# BLOQUÉ EN V0 : le mode deeplink ne construit pas de tx dict.
# Câblé correctement pour V1 (quand PendleAPYito construira
# ses propres transactions).
# ============================================================

def _kit_estimate_gas_usd(
    chain: str,
    tx: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Appelle defi_fee_kit.FeePolicy.estimate(tx, chain).

    V0 : renvoie None (pas de tx à estimer en mode deeplink).
    V1 : instancier FeePolicy avec les providers rpc + price.
    """
    if not HAS_FEE_KIT or not HAS_RPC_KIT or not HAS_PRICE_KIT:
        return None
    if tx is None:
        return None

    try:
        # TODO V1 :
        # policy = FeePolicy.from_env(
        #     rpc_provider=_get_rpc_provider(chain),
        #     price_provider=_get_price_provider(),
        # )
        # result = policy.estimate(tx=tx, chain=chain)
        # return result if isinstance(result, dict) and result.get("ok") else None
        return None
    except Exception:
        return None


# ============================================================
# ZONE SIGNATURES KITS - RPC
# ------------------------------------------------------------
# Signatures vérifiées le 2026-07-07 sur le code réel de defi_rpc_kit :
#   - RpcProvider.from_env(chain: str, profile="read", timeout_sec=None) → instance
#   - provider.gas_price()  → int (wei, passthrough brut)
#   - provider.health()     → dict {chain, connected, block_number,
#                                    provider_url, timeout_sec, profile}
#   - provider.last_used_url, provider.is_connected (property)
# ============================================================

def _kit_get_gas_price_wei(chain: str) -> Optional[int]:
    provider = _get_rpc_provider(chain)
    if provider is None:
        return None
    try:
        return provider.gas_price()
    except Exception:
        return None

def _kit_get_rpc_health(chain: str) -> Optional[Dict[str, Any]]:
    provider = _get_rpc_provider(chain)
    if provider is None:
        return None
    try:
        return provider.health()
    except Exception:
        return None

# ============================================================
# FIN ZONE SIGNATURES KITS
# ============================================================


# ============================================================
# API publique consommée par l'UI
# ============================================================

def get_price_usd(symbol: str) -> Optional[float]:
    """Prix spot USD d'un gas token (ex: "ETH"). None si kit absent ou échec."""
    return _kit_fetch_price_usd(symbol)


def get_prices_for_chains(chains: List[str]) -> Dict[str, Optional[float]]:
    """Retourne {gas_token: prix_usd} pour les chaînes présentes.

    Utilisé par le bandeau prix du cockpit. Dict vide si kit prix absent.
    Tokens dont le prix n'est pas disponible sur les CEX → valeur None.
    """
    if not HAS_PRICE_KIT:
        return {}
    result: Dict[str, Optional[float]] = {}
    for sym in gas_tokens_for_chains(chains):
        result[sym] = get_price_usd(sym)
    return result


def estimate_gas(
    chain: str,
    tx: Optional[Dict[str, Any]] = None,
    action_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimation gas OFFICIELLE (fee_kit) — nécessite un tx dict.

    V0 deeplink : available=False (pas de tx à estimer).
    V1 exécution : passera le tx au fee_kit et retournera l'estimation précise.
    Pour l'estimation indicative en mode deeplink, voir estimate_gas_indicative().
    """
    raw = _kit_estimate_gas_usd(chain, tx)
    if raw is None:
        return {
            "available": False,
            "fee_usd": None,
            "max_usd": FEE_MAX_USD_PER_TX,
            "exceeds_max": False,
            "paid_by": "self_paid",
            "reason": "no_tx_in_deeplink_mode",
        }

    fee_usd = raw.get("user_cost_usd") or raw.get("gas_cost_usd")
    available = fee_usd is not None
    exceeds = bool(available and fee_usd > FEE_MAX_USD_PER_TX)
    return {
        "available": available,
        "fee_usd": fee_usd,
        "max_usd": FEE_MAX_USD_PER_TX,
        "exceeds_max": exceeds,
        "paid_by": "self_paid",
    }


def estimate_gas_indicative(
    chain: str,
    action_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Estimation gas INDICATIVE pour le mode deeplink.

    Calcul : gas_units(action) × gas_price_wei × gas_token_price_usd / 1e18.
    Indépendant du fee_kit : ne nécessite AUCUN tx dict.
    Utilise directement rpc_kit.gas_price() + price_kit.get_price().

    C'est un ORDRE DE GRANDEUR — pas un chiffre exact.
    Utile pour donner à l'utilisateur une idée du coût avant clic deeplink.
    """
    empty: Dict[str, Any] = {
        "available": False,
        "gas_units": None,
        "gas_price_gwei": None,
        "gas_token": None,
        "gas_token_price_usd": None,
        "fee_native": None,
        "fee_usd": None,
        "max_usd": FEE_MAX_USD_PER_TX,
        "exceeds_max": False,
        "reason": None,
    }

    if not HAS_RPC_KIT or not HAS_PRICE_KIT:
        empty["reason"] = "kits_unavailable"
        return empty

    gas_token = gas_token_for_chain(chain)
    if not gas_token:
        empty["reason"] = f"unknown_chain:{chain}"
        return empty

    gas_units = action_gas_units(action_type)
    gas_price_wei = _kit_get_gas_price_wei(chain)
    token_price_usd = get_price_usd(gas_token)

    # new_str
    if gas_price_wei is None:
        # Fallback statique pour les chaînes non encore dans le CHAIN_ENV_MAP
        # du defi_rpc_kit (monad, plasma, bnb, hyperliquid...).
        # Valeurs conservatrices — à remplacer par le vrai gas_price dès que
        # le kit sera enrichi côté transak_kit.
        _FALLBACK_GWEI: Dict[str, float] = {
            "MON": 0.5,  # Monad : réseau récent, fees très bas
            "XPL": 0.5,  # Plasma : même ordre
            "BNB": 1.0,  # BSC : historiquement ~1 gwei
            "HYPE": 0.5,  # HyperEVM : fees bas
        }
        fallback_gwei = _FALLBACK_GWEI.get(gas_token)
        if fallback_gwei is not None and token_price_usd is not None:
            gas_price_wei = int(fallback_gwei * 1e9)
            fee_native = (gas_units * gas_price_wei) / 1e18
            fee_usd = fee_native * token_price_usd
            exceeds = fee_usd > FEE_MAX_USD_PER_TX
            return {
                "available": True,
                "gas_units": gas_units,
                "gas_price_gwei": fallback_gwei,
                "gas_token": gas_token,
                "gas_token_price_usd": token_price_usd,
                "fee_native": fee_native,
                "fee_usd": fee_usd,
                "max_usd": FEE_MAX_USD_PER_TX,
                "exceeds_max": exceeds,
                "reason": "fallback_static_gwei",  # signale que c'est estimatif
            }
        empty["gas_token"] = gas_token
        empty["reason"] = "no_gas_price"
        return empty

    if token_price_usd is None:
        empty["gas_token"] = gas_token
        empty["gas_price_gwei"] = gas_price_wei / 1e9
        empty["reason"] = f"no_price_for_{gas_token}"
        return empty

    fee_native = (gas_units * gas_price_wei) / 1e18
    fee_usd = fee_native * token_price_usd
    exceeds = fee_usd > FEE_MAX_USD_PER_TX

    return {
        "available": True,
        "gas_units": gas_units,
        "gas_price_gwei": gas_price_wei / 1e9,
        "gas_token": gas_token,
        "gas_token_price_usd": token_price_usd,
        "fee_native": fee_native,
        "fee_usd": fee_usd,
        "max_usd": FEE_MAX_USD_PER_TX,
        "exceeds_max": exceeds,
        "reason": None,
    }


def rpc_health(chain: str) -> Dict[str, Any]:
    """État de santé RPC pour une chaîne. Dict stable, jamais d'exception.

    Utilisé par le badge RPC du cockpit (Option A : une chaîne à la fois).
    Passe la chaîne du dernier market fetché, ou "ethereum" par défaut.

    Format retourné à l'UI (contrat stable) :
        {
          "available": bool,        # kit installé + provider instancié
          "ok": bool,               # connected==True côté kit
          "chain": str,
          "block_number": int | None,
          "provider_url": str | None,
          "reason": str | None,     # renseigné quand !ok
        }
    """
    if not HAS_RPC_KIT:
        return {
            "available": False,
            "ok": False,
            "chain": chain,
            "block_number": None,
            "provider_url": None,
            "reason": "rpc_kit_absent",
        }

    raw = _kit_get_rpc_health(chain)
    if raw is None:
        return {
            "available": False,
            "ok": False,
            "chain": chain,
            "block_number": None,
            "provider_url": None,
            "reason": "provider_unavailable",
        }

    connected = bool(raw.get("connected"))
    return {
        "available": True,
        "ok": connected,
        "chain": raw.get("chain") or chain,
        "block_number": raw.get("block_number"),
        "provider_url": raw.get("provider_url"),
        "reason": None if connected else "not_connected",
    }