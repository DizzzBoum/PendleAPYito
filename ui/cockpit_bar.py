"""
Bandeau cockpit : prix gas tokens + badge santé RPC.
Rendu inline dans app.py, entre le caption et les onglets.

Aucun onglet, aucune exécution : lecture seule via kits_bridge.
Si les kits sont absents, le bandeau ne s'affiche pas (silencieux).
"""

from __future__ import annotations

import json
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import streamlit as st

from config import MARKETS_FILE
from adapters.kits_bridge import (
    HAS_PRICE_KIT,
    HAS_RPC_KIT,
    get_prices_for_chains,
    rpc_health,
)


# ============================================================
# Helpers
# ============================================================

def _load_chains_from_markets() -> Tuple[List[str], str]:
    """Lit markets.json et retourne (chains_présentes, chaîne_principale).

    Chaîne principale = 1re chaîne trouvée dans markets.json.
    Fallback "ethereum" si cache vide ou illisible.
    """
    if not MARKETS_FILE.exists():
        return [], "ethereum"
    try:
        data = json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
        chains: List[str] = []
        for m in data:
            ch = (m.get("chain") or "").strip().lower()
            if ch and ch not in chains:
                chains.append(ch)
        primary = chains[0] if chains else "ethereum"
        return chains, primary
    except Exception:
        return [], "ethereum"


def _mask_provider_url(url: Optional[str]) -> str:
    """Retourne le host seulement, jamais le path (qui peut contenir une clé API).

    Ex: "https://eth-mainnet.g.alchemy.com/v2/ABC123" → "eth-mainnet.g.alchemy.com"
    """
    if not url:
        return "—"
    try:
        parsed = urlparse(url)
        return parsed.netloc or "—"
    except Exception:
        return "—"


def _fmt_price(v: Optional[float]) -> Optional[str]:
    """Format compact pour le bandeau.

    Règle affichage :
    - Séparateur décimal : virgule (pas de point)
    - Séparateur milliers : aucun
    - >= 100 → entier     ex: $1737
    - >= 1   → 2 décimales  ex: $67,28
    - < 1    → 4 décimales  ex: $0,0912
    """
    if v is None:
        return None
    if v >= 100:
        return f"${v:.0f}"
    if v >= 1:
        return f"${v:.2f}".replace(".", ",")
    return f"${v:.4f}".replace(".", ",")


# ============================================================
# Styles locaux (extension du thème AnyLiqBot sans modifier _theme.py)
# ============================================================

def _inject_local_styles() -> None:
    """Ajoute une classe .is-ok verte au vocabulaire de chips existant,
    plus le style des mini-badges prix. Ne touche pas _theme.py.
    """
    st.markdown(
        """
<style>
# new_str
/* Extension du thème : état "ok" reprend --neo-blue (cyan du thème AnyLiqBot) */
.any-chip.is-ok, .chip.is-ok {
  --c: var(--neo-blue);
  --csoft: var(--neo-blue-soft);
}

/* Badge RPC dans la barre cockpit : taille légèrement réduite */
.cockpit-bar .any-chip {
  padding: 5px 10px;
}
.cockpit-bar .any-chip .label {
  font-size: 12px;
}
.cockpit-bar .any-chip .muted {
  font-size: 11px;
}

/* Mini-badge prix (léger, sans laser trim — on garde le trim pour le badge RPC) */
.cockpit-price {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(148,163,184,0.14);
  font-size: 13px;
}
.cockpit-price .sym {
  color: rgba(226,232,240,0.72);
  font-weight: 800;
  letter-spacing: 0.5px;
}
.cockpit-price .val {
  color: rgba(255,255,255,0.94);
  font-weight: 900;
}
.cockpit-price .val.na {
  color: rgba(148,163,184,0.55);
  font-weight: 700;
}

/* Pousse le badge RPC à droite du bandeau */
.cockpit-spacer { flex: 1 1 auto; }
</style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Construction HTML
# ============================================================

def _price_chip_html(sym: str, price: Optional[float]) -> str:
    val = _fmt_price(price)
    if val is None:
        return (
            f'<span class="cockpit-price">'
            f'<span class="sym">{sym}</span>'
            f'<span class="val na">—</span>'
            f'</span>'
        )
    return (
        f'<span class="cockpit-price">'
        f'<span class="sym">{sym}</span>'
        f'<span class="val">{val}</span>'
        f'</span>'
    )


def _rpc_chip_html(health: dict) -> str:
    """Chip RPC utilisant .any-chip du thème + état .is-ok (vert) ou .is-error (rose).

    Le point LED reprend l'animation halo/laser trim déjà définie dans _theme.py.
    """
    # new_str
    ok = bool(health.get("ok"))
    chain = health.get("chain") or "—"
    host = _mask_provider_url(health.get("provider_url"))

    state_class = "is-ok" if ok else "is-error"
    label = "RPC OK" if ok else "RPC KO"

    if ok:
        detail = f"{chain} · {host}"
    else:
        reason = health.get("reason") or "erreur"
        detail = f"{chain} · {reason}"

    return (
        f'<span class="any-chip {state_class}">'
        f'<span class="any-led on"></span>'
        f'<span class="label">{label}</span>'
        f'<span class="muted">{detail}</span>'
        f'</span>'
    )


# ============================================================
# Point d'entrée
# ============================================================

# new_str
# ============================================================
# Wrappers cachés — les appels réseau (CEX + RPC) ne se refont
# pas à chaque interaction Streamlit. TTL = 30s.
# st.cache_data exige des arguments hashables → tuple pour les listes.
# Ces fonctions sont dans cockpit_bar.py (pas dans kits_bridge.py
# qui doit rester sans import streamlit).
# ============================================================

@st.cache_data(ttl=30)
def _cached_prices(chains_tuple: tuple) -> dict:
    """Prix gas tokens — 1 seul fetch CEX toutes les 30s."""
    return get_prices_for_chains(list(chains_tuple))


@st.cache_data(ttl=30)
def _cached_rpc_health(chain: str) -> dict:
    """Santé RPC — 1 seul appel Alchemy toutes les 30s."""
    return rpc_health(chain)


@st.cache_data(ttl=60)
def _cached_load_chains() -> tuple:
    """Chaînes depuis markets.json — 1 seule lecture toutes les 60s."""
    chains, primary = _load_chains_from_markets()
    return tuple(chains), primary


def render_cockpit_bar() -> None:
    """Affiche le bandeau prix (gauche) + badge RPC (droite).

    Utilise st.columns pour le positionnement gauche/droite —
    le flexbox HTML pur ne s'étend pas correctement dans le conteneur
    Streamlit. Le HTML reste utilisé uniquement pour les chips elles-mêmes.
    Silencieux si aucun kit disponible.
    """
    chains_tuple, primary_chain = _cached_load_chains()

    prices = _cached_prices(chains_tuple) if HAS_PRICE_KIT else {}
    health = _cached_rpc_health(primary_chain) if HAS_RPC_KIT else None

    if not prices and not health:
        return

    _inject_local_styles()

    col_prix, col_rpc = st.columns([5, 2])

    with col_prix:
        if prices:
            chips = "".join(_price_chip_html(sym, p) for sym, p in prices.items())
            st.markdown(
                f'<div class="cockpit-bar">{chips}</div>',
                unsafe_allow_html=True,
            )

    with col_rpc:
        if health:
            st.markdown(
                f'<div style="display:flex;justify-content:flex-end;'
                f'align-items:center;height:100%;padding-top:2px;">'
                f'{_rpc_chip_html(health)}</div>',
                unsafe_allow_html=True,
            )