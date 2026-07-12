import json
from datetime import datetime, date

import pandas as pd
import streamlit as st
pd.set_option('future.no_silent_downcasting', True)
from adapters.pendle_api import PendleAPI
from config import (
    DATA_DIR,
    MARKETS_FILE,
    PENDLE_API_BASE,
    DEFAULT_TIMEOUT,
    DEFAULT_MIN_TVL_USD,
    DEFAULT_MIN_APY,
)

def _format_usd_short(value):
    if value is None:
        return "-"

    try:
        value = float(value)

        if value >= 1_000_000_000:
            return f"{value/1_000_000_000:.1f}B"
        elif value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.1f}k"
        else:
            return f"{value:.0f}"

    except Exception:
        return str(value)
# ============================================================
# Helpers internes
# ============================================================

def _safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _parse_maturity_to_date(value):
    """
    Essaie de convertir une maturité en date.
    Gère plusieurs formats possibles.
    """
    if not value:
        return None

    # Cas timestamp numérique
    if isinstance(value, (int, float)):
        try:
            return datetime.utcfromtimestamp(value).date()
        except Exception:
            return None

    # Cas string ISO
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except Exception:
            pass

        # Cas YYYY-MM-DD
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").date()
        except Exception:
            return None

    return None


def _detect_asset_type(symbol: str) -> str:
    """
    Détection simple du type d'actif pour les filtres V1.
    """
    s = (symbol or "").lower()

    stable_keywords = [
        "usdc", "usdt", "dai", "usde", "fdusd", "susde", "usdy", "usd0"
    ]
    eth_keywords = ["eth", "weth", "weeth", "ezeth", "reth", "steth"]
    btc_keywords = ["btc", "wbtc", "cbbtc"]

    if any(k in s for k in stable_keywords):
        return "stable"
    if any(k in s for k in eth_keywords):
        return "eth"
    if any(k in s for k in btc_keywords):
        return "btc"
    return "other"


def _normalize_markets(raw: dict) -> list[dict]:
    items = raw.get("results", [])

    today = date.today()
    normalized = []

    chain_map = {
        1: "ethereum",
        10: "optimism",
        56: "bnb",
        137: "polygon",
        143: "monad",
        146: "sonic",
        999: "hyperevm",
        5000: "mantle",
        8453: "base",
        9745: "plasma",
        42161: "arbitrum",
        80094: "berachain",
    }

    for item in items:
        details = item.get("details") or {}

        # ===== ID / NAME =====
        market_id = item.get("address")
        market_name = item.get("name") or "unknown_market"

        # ===== CHAIN =====
        chain_id = item.get("chainId")
        chain = chain_map.get(chain_id, str(chain_id) if chain_id is not None else "unknown")

        # ===== ASSET SYMBOL =====
        # L'endpoint actuel ne fournit pas directement un dict avec symbol.
        # On prend donc un fallback depuis le nom du market.
        asset_symbol = None

        raw_underlying = item.get("underlyingAsset")
        if isinstance(raw_underlying, dict):
            asset_symbol = raw_underlying.get("symbol")

        if not asset_symbol and market_name:
            # Exemple:
            # "sUSDe (Bera Concrete)" -> "sUSDe"
            # "pufETH" -> "pufETH"
            # "USD0++" -> "USD0++"
            asset_symbol = market_name.split(" (")[0].strip()

        # ===== MATURITY =====
        maturity_raw = item.get("expiry") or item.get("maturity")
        maturity_date = _parse_maturity_to_date(maturity_raw)
        days_to_maturity = (maturity_date - today).days if maturity_date else None

        # ===== APY =====
        # Les vraies valeurs sont dans details
        implied_apy = _safe_float(details.get("impliedApy"))
        underlying_apy = _safe_float(details.get("underlyingApy"))
        aggregated_apy = _safe_float(details.get("aggregatedApy"))

        # Priorité : aggregated > implied
        final_apy = aggregated_apy if aggregated_apy is not None else implied_apy

        # Si l'API renvoie un ratio (ex: 0.12), on le convertit en %
        if final_apy is not None and final_apy <= 1:
            final_apy *= 100

        if underlying_apy is not None and underlying_apy <= 1:
            underlying_apy *= 100

        # Garde-fou : écarter les APY aberrants (> 1000%)
        # Certains marchés morts / illiquides renvoient des ratios explosés.
        APY_MAX_SANE = 1000.0
        if final_apy is not None and (final_apy < 0 or final_apy > APY_MAX_SANE):
            final_apy = None
        if underlying_apy is not None and (underlying_apy < 0 or underlying_apy > APY_MAX_SANE):
            underlying_apy = None

        # ===== TVL / VOLUME =====
        tvl_usd = _safe_float(details.get("totalTvl"))
        if tvl_usd is None:
            tvl_usd = _safe_float(details.get("liquidity"))

        volume_24h = _safe_float(details.get("tradingVolume"))

        # ===== APY LP BOOSTÉ (vePENDLE) =====
        lp_max_boosted_apy = _safe_float(details.get("maxBoostedApy"))
        if lp_max_boosted_apy is not None and lp_max_boosted_apy <= 1:
            lp_max_boosted_apy *= 100
        if lp_max_boosted_apy is not None and (lp_max_boosted_apy < 0 or lp_max_boosted_apy > APY_MAX_SANE):
            lp_max_boosted_apy = None

        # ===== POINTS / AIRDROP (multiplicateurs) =====
        points_list = item.get("points") or []
        points_str = ""
        if points_list:
            parts = []
            for p in points_list:
                key = p.get("key") or "?"
                val = p.get("value")
                if val and val != 1:
                    parts.append(f"{key} ×{val}")
                else:
                    parts.append(key)
            points_str = ", ".join(parts)

        # ===== TYPE D'ACTIF =====
        category_ids = item.get("categoryIds") or []
        if "stables" in category_ids:
            asset_type = "stable"
        else:
            asset_type = _detect_asset_type(asset_symbol or "")

        # ===== MARKET INFO (fiche détail) =====
        market_info = item.get("marketInfo") or {}

        def _strip_html(txt):
            if not txt:
                return ""
            import re
            return re.sub(r"<[^>]+>", "", str(txt)).strip()

        info_description = _strip_html(market_info.get("assetDescription"))
        info_risk = _strip_html(market_info.get("riskInvolved"))
        info_quirks_raw = _strip_html(market_info.get("importantQuirks"))
        # On masque les quirks génériques
        info_quirks = "" if "no special quirks" in info_quirks_raw.lower() else info_quirks_raw

        conv = market_info.get("conversionRate") or {}
        info_conversion = ""
        if conv.get("rate"):
            info_conversion = f"1 {conv.get('fromUnit', '?')} = {conv.get('rate'):.4f} {conv.get('toUnit', '?')}"

        protocols = market_info.get("utilizedProtocols") or []
        info_protocols = ", ".join(p.get("name", "?") for p in protocols) if protocols else ""

        deposit = market_info.get("deposit") or {}
        info_deposit_url = deposit.get("url") or ""

        # ===== ACTIVE =====
        # On considère actif par défaut si non expiré
        is_active = True
        if days_to_maturity is not None and days_to_maturity < 0:
            is_active = False

        normalized.append({
            "market_id": market_id,
            "market_name": market_name,
            "chain": chain,
            "asset_symbol": asset_symbol,
            "asset_type": asset_type,
            "implied_apy": final_apy,
            "underlying_apy": underlying_apy,
            "maturity_date": str(maturity_date) if maturity_date else None,
            "days_to_maturity": days_to_maturity,
            "tvl_usd": tvl_usd,
            "volume_24h": volume_24h,
            "lp_max_boosted_apy": lp_max_boosted_apy,
            "points": points_str,
            "info_description": info_description,
            "info_risk": info_risk,
            "info_quirks": info_quirks,
            "info_conversion": info_conversion,
            "info_protocols": info_protocols,
            "info_deposit_url": info_deposit_url,
            "is_active": is_active,
        })

    return normalized


def _save_markets(markets: list[dict], merge: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if merge and MARKETS_FILE.exists():
        try:
            existing = json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = []

        # Chaînes présentes dans le nouveau fetch
        new_chains = set(m.get("chain") for m in markets)

        # Garder les marchés des autres chaînes
        merged = [m for m in existing if m.get("chain") not in new_chains]
        merged.extend(markets)
        markets = merged

    MARKETS_FILE.write_text(
        json.dumps(markets, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# new_str
@st.cache_data(ttl=300)
def _load_markets_from_disk() -> list[dict]:
    """Lit markets.json depuis le disque. Cache 5 min (TTL=300s).

    Le fichier ne change que sur Refresh markets / Refresh ALL :
    ces boutons appellent st.cache_data.clear() pour invalider
    le cache immédiatement après la mise à jour.
    """
    if not MARKETS_FILE.exists():
        return []
    try:
        return json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _refresh_markets_from_api(chain_id: int = None) -> list[dict]:
    api = PendleAPI(base_url=PENDLE_API_BASE, timeout=DEFAULT_TIMEOUT)
    raw = api.get_all_markets(limit=100, skip=0, chain_id=chain_id)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Sauvegarde de la réponse brute pour inspection
    raw_file = DATA_DIR / "markets_raw.json"
    raw_file.write_text(
        json.dumps(raw, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    markets = _normalize_markets(raw)
    _save_markets(markets, merge=True)
    return markets

def _refresh_all_markets_crosschain() -> list[dict]:
    """
    Récupère TOUS les marchés Pendle cross-chain en une seule passe paginée.

    Remplace la boucle 8 appels chaîne par chaîne du bouton Refresh ALL.
    Utilise fetch_all_pages() sans chain_id : l'API renvoie toutes les chaînes.
    Écrase markets.json (merge=False) : la passe est complète, on ne fusionne pas.
    """
    api = PendleAPI(base_url=PENDLE_API_BASE, timeout=DEFAULT_TIMEOUT)
    all_raw_items = api.fetch_all_pages(chain_id=None, page_size=100, max_pages=10)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Sauvegarde brute pour debug (concaténation de toutes les pages)
    raw_file = DATA_DIR / "markets_raw.json"
    raw_file.write_text(
        json.dumps(
            {"results": all_raw_items, "total": len(all_raw_items)},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    markets = _normalize_markets({"results": all_raw_items})
    _save_markets(markets, merge=False)  # écrase tout — passe complète
    return markets

# ============================================================
# UI principale
# ============================================================

def render_market_scan():
    st.subheader("Market Scan")

    # ============================================================
    # Initialisation des valeurs de filtres (une seule fois)
    # Évite le conflit Streamlit value= + session_state
    # ============================================================
    _filter_defaults = {
        "market_scan_asset_type": "ALL",
        "market_scan_chain": "ALL",
        "market_scan_min_apy": float(DEFAULT_MIN_APY),
        "market_scan_min_tvl": int(DEFAULT_MIN_TVL_USD),
        "market_scan_min_days": 0,
        "market_scan_max_days": 0,
    }
    for _k, _v in _filter_defaults.items():
        if _k not in st.session_state:
            st.session_state[_k] = _v
    # ============================================================
    # Chaînes disponibles pour le fetch
    # ============================================================

    FETCH_CHAINS = {
        "Ethereum": 1,
        "Base": 8453,
        "BNB": 56,
        "Arbitrum": 42161,
        "Optimism": 10,
        "HyperEVM": 999,
        "Monad": 143,
        "Plasma": 9745,
    }

    col_chain, col_a, col_b, col_c = st.columns([3, 1, 1, 1])

    with col_chain:
        st.caption("Chaîne à récupérer")
        fetch_chain_label = st.selectbox(
            "Chaîne à récupérer",
            list(FETCH_CHAINS.keys()),
            key="market_scan_fetch_chain",
            label_visibility="collapsed",
        )
        fetch_chain_id = FETCH_CHAINS[fetch_chain_label]

    with col_a:
        st.caption(" ")
        if st.button("Refresh markets", width="stretch"):
            try:
                markets = _refresh_markets_from_api(chain_id=fetch_chain_id)
                st.cache_data.clear()  # force rechargement depuis le nouveau JSON
                st.success(f"{len(markets)} marchés mis à jour.")
            except Exception as e:
                st.error(f"Erreur API Pendle : {e}")

    with col_b:
        st.caption(" ")
        if st.button("🌐 Refresh ALL", width="stretch"):
            try:
                with st.spinner("Récupération cross-chain en cours…"):
                    markets = _refresh_all_markets_crosschain()
                st.cache_data.clear()
                st.success(f"{len(markets)} marchés chargés toutes chaînes.")
            except Exception as e:
                st.error(f"Erreur Refresh ALL : {e}")

    with col_c:
        st.caption(" ")
        if st.button("Reload cache local", width="stretch"):
            st.cache_data.clear()  # force relecture immédiate de markets.json
            st.info("Cache local rechargé.")

    # Chargement principal
    markets = _load_markets_from_disk()

    # Si aucun cache, tentative de fetch direct
    if not markets:
        try:
            markets = _refresh_markets_from_api()
            st.caption("Aucun cache trouvé : chargement initial effectué depuis l'API.")
        except Exception as e:
            st.warning("Impossible de charger les marchés pour le moment.")
            st.code(str(e))
            return

    df = pd.DataFrame(markets)
    with st.expander("Debug Market Scan"):
        st.write("Nombre d'entrées normalisées :", len(markets))
        st.write("Colonnes du DataFrame :", df.columns.tolist())

        if not df.empty:
            st.write("Aperçu normalisé :")
            st.dataframe(df.head(10), width="stretch", hide_index=True)

        raw_file = DATA_DIR / "markets_raw.json"
        if raw_file.exists():
            try:
                raw_data = json.loads(raw_file.read_text(encoding="utf-8"))
                st.write("Clés racine de la réponse brute :", list(raw_data.keys()))

                # Aperçu léger du brut
                if isinstance(raw_data, dict):
                    if "results" in raw_data and isinstance(raw_data["results"], list) and raw_data["results"]:
                        st.write("Premier objet brut depuis raw['results'] :")
                        st.json(raw_data["results"][0])
                    elif "markets" in raw_data and isinstance(raw_data["markets"], list) and raw_data["markets"]:
                        st.write("Premier objet brut depuis raw['markets'] :")
                        st.json(raw_data["markets"][0])
                    elif "data" in raw_data and isinstance(raw_data["data"], list) and raw_data["data"]:
                        st.write("Premier objet brut depuis raw['data'] :")
                        st.json(raw_data["data"][0])
                    else:
                        st.write("Réponse brute complète :")
                        st.json(raw_data)
            except Exception as e:
                st.warning(f"Impossible de lire markets_raw.json : {e}")

    if df.empty:
        st.info("Aucun marché disponible.")
        return

    # ========================================================
    # KPIs rapides
    # ========================================================
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Marchés", len(df))

    with k2:
        max_apy = df["implied_apy"].dropna().max() if "implied_apy" in df.columns else None
        st.metric("Meilleur APY", f"{max_apy:.2f}%" if pd.notna(max_apy) else "-")

    with k3:
        stable_count = len(df[df["asset_type"] == "stable"]) if "asset_type" in df.columns else 0
        st.metric("Marchés stable", stable_count)

    with k4:
        low_maturity_count = len(df[df["days_to_maturity"].fillna(99999) <= 30]) if "days_to_maturity" in df.columns else 0
        st.metric("Maturité ≤ 30j", low_maturity_count)

    st.divider()

    # ========================================================
    # Filtres rapides
    # ========================================================
    st.caption("Filtres rapides")
    qf1, qf2, qf3, qf4 = st.columns(4)

    with qf1:
        if st.button("💵 Stables only", key="qf_stables", width="stretch"):
            st.session_state["market_scan_asset_type"] = "stable"
            st.rerun()

    with qf2:
        if st.button("🚀 APY > 5%", key="qf_apy5", width="stretch"):
            st.session_state["market_scan_min_apy"] = 5.0
            st.rerun()

    with qf3:
        if st.button("⏳ Maturité 30-90j", key="qf_maturity", width="stretch"):
            st.session_state["market_scan_min_days"] = 30
            st.session_state["market_scan_max_days"] = 90
            st.rerun()

    with qf4:
        if st.button("🔄 Réinitialiser", key="qf_reset", width="stretch"):
            st.session_state["market_scan_asset_type"] = "ALL"
            st.session_state["market_scan_chain"] = "ALL"
            st.session_state["market_scan_min_apy"] = float(DEFAULT_MIN_APY)
            st.session_state["market_scan_min_tvl"] = int(DEFAULT_MIN_TVL_USD)
            st.session_state["market_scan_min_days"] = 0
            st.session_state["market_scan_max_days"] = 0
            st.rerun()

    # ========================================================
    # Filtres
    # ========================================================
    f1, f2, f3, f4 = st.columns(4)

    chains = ["ALL"]
    if "chain" in df.columns:
        chains += sorted([x for x in df["chain"].dropna().astype(str).unique().tolist()])

    asset_types = ["ALL"]
    if "asset_type" in df.columns:
            asset_types += sorted([x for x in df["asset_type"].dropna().astype(str).unique().tolist()])

    # Garde-fou : si la valeur stockée n'existe plus dans les options, on retombe sur ALL
    if st.session_state.get("market_scan_chain") not in chains:
        st.session_state["market_scan_chain"] = "ALL"
    if st.session_state.get("market_scan_asset_type") not in asset_types:
        st.session_state["market_scan_asset_type"] = "ALL"

    with f1:
        selected_chain = st.selectbox("Chaîne", chains, key="market_scan_chain")

    with f2:
        selected_asset_type = st.selectbox(
            "Type d'actif", asset_types, key="market_scan_asset_type"
        )

    with f3:
        min_apy = st.number_input(
            "APY min (%)",
            min_value=0.0,
            step=0.5,
            key="market_scan_min_apy",
        )

    with f4:
        min_tvl = st.number_input(
            "TVL min ($)",
            min_value=0,
            step=50000,
            key="market_scan_min_tvl",
        )

    g1, g2, g3 = st.columns(3)

    with g1:
        only_active = st.checkbox(
            "Afficher seulement les marchés actifs",
            value=True,
            key="market_scan_only_active",
        )
    with g2:
        min_days_to_maturity = st.number_input(
            "Maturité min (jours, 0 = ignore)",
            min_value=0,
            step=15,
            key="market_scan_min_days",
        )
    with g3:
        max_days_to_maturity = st.number_input(
            "Maturité max (jours, 0 = ignore)",
            min_value=0,
            step=30,
            key="market_scan_max_days",
        )

    # ========================================================
    # Filtrage
    # ========================================================
    filtered = df.copy()

    if selected_chain != "ALL":
        filtered = filtered[filtered["chain"] == selected_chain]

    if selected_asset_type != "ALL":
        filtered = filtered[filtered["asset_type"] == selected_asset_type]

    filtered["implied_apy"] = pd.to_numeric(
        filtered["implied_apy"], errors="coerce"
    )
    filtered["implied_apy"] = filtered["implied_apy"].where(
        filtered["implied_apy"].notna(), 0.0
    )

    filtered["tvl_usd"] = pd.to_numeric(
        filtered["tvl_usd"], errors="coerce"
    )
    filtered["tvl_usd"] = filtered["tvl_usd"].where(
        filtered["tvl_usd"].notna(), 0.0
    )

    if "days_to_maturity" in filtered.columns:
        filtered["days_to_maturity"] = pd.to_numeric(
            filtered["days_to_maturity"], errors="coerce"
        )
        filtered["days_to_maturity"] = filtered["days_to_maturity"].where(
            filtered["days_to_maturity"].notna(), 999999
        )

    filtered = filtered[filtered["implied_apy"] >= min_apy]
    filtered = filtered[filtered["tvl_usd"] >= min_tvl]

    if only_active and "is_active" in filtered.columns:
        filtered["is_active"] = filtered["is_active"].astype("boolean")
        filtered["is_active"] = filtered["is_active"].where(
            filtered["is_active"].notna(), False
        )
        filtered = filtered[filtered["is_active"]]

        # Exclure marchés expirés (sécurité indépendante du cache is_active)
    if "days_to_maturity" in filtered.columns:
        filtered = filtered[filtered["days_to_maturity"] >= 0]

    if max_days_to_maturity > 0 and "days_to_maturity" in filtered.columns:
        filtered = filtered[
            filtered["days_to_maturity"] <= max_days_to_maturity
            ]
    if min_days_to_maturity > 0 and "days_to_maturity" in filtered.columns:
        filtered = filtered[filtered["days_to_maturity"] >= min_days_to_maturity]

        # Garde-fou : aucun marché après filtrage
    if filtered.empty:
        st.caption("0 marché(x) affiché(s) avec les filtres actuels.")
        return

    # Tri principal

    # ========================================================
    # Intelligence PT MVP
    # ========================================================

    def _score_pt_row(row):
        score = 0
        comments = []

        apy = row.get("implied_apy")
        days = row.get("days_to_maturity")
        tvl = row.get("tvl_usd")
        asset_type = row.get("asset_type")

        # ----------------------------------------------------
        # APY
        # ----------------------------------------------------
        if apy is not None:
            try:
                apy = float(apy)
                if apy >= 8:
                    score += 40
                    comments.append("bon rendement")
                elif apy >= 5:
                    score += 25
                    comments.append("rendement correct")
                elif apy >= 2:
                    score += 10
                    comments.append("rendement modeste")
                else:
                    comments.append("rendement faible")
            except Exception:
                comments.append("apy non lisible")

        # ----------------------------------------------------
        # Maturité
        # ----------------------------------------------------
        if days is not None:
            try:
                days = int(float(days))
                if 21 <= days <= 180:
                    score += 30
                    comments.append("maturité intéressante")
                elif 7 <= days <= 20:
                    score += 10
                    comments.append("maturité courte")
                elif days > 180:
                    score += 10
                    comments.append("maturité longue")
                elif days < 7:
                    comments.append("très proche maturité")
            except Exception:
                comments.append("maturité non lisible")

        # ----------------------------------------------------
        # TVL
        # ----------------------------------------------------
        if tvl is not None:
            try:
                tvl = float(tvl)
                if tvl >= 1_000_000:
                    score += 30
                    comments.append("TVL solide")
                elif tvl >= 250_000:
                    score += 20
                    comments.append("TVL correcte")
                elif tvl >= 50_000:
                    score += 10
                    comments.append("TVL moyenne")
                else:
                    comments.append("TVL faible")
            except Exception:
                comments.append("TVL non lisible")

        # ----------------------------------------------------
        # Spread APY implicite vs underlying (PT potentiellement sous/sur-évalué)
        # ----------------------------------------------------
        underlying_apy_val = row.get("underlying_apy")
        if apy is not None and underlying_apy_val is not None:
            try:
                underlying_apy_val = float(underlying_apy_val)
                spread = apy - underlying_apy_val
                if spread >= 3:
                    score += 15
                    comments.append("spread favorable")
                elif spread <= -3:
                    score -= 10
                    comments.append("spread défavorable")
            except Exception:
                pass
        # ----------------------------------------------------
        # Bonus stable (facultatif, léger)
        # ----------------------------------------------------
        if asset_type == "stable":
            score += 5
            comments.append("profil stable")

        # ----------------------------------------------------
        # Signal final
        # ----------------------------------------------------
        if score >= 75:
            signal = "🟢 Bon PT"
        elif score >= 45:
            signal = "🟡 PT correct"
        else:
            signal = "🔴 PT faible"

        return score, signal, " | ".join(comments)

    pt_results = filtered.apply(_score_pt_row, axis=1, result_type="expand")
    pt_results.columns = ["pt_score", "pt_signal", "pt_comment"]

    filtered["pt_score"] = pt_results["pt_score"]
    filtered["pt_signal"] = pt_results["pt_signal"]
    filtered["pt_comment"] = pt_results["pt_comment"]

    # ========================================================
    # Intelligence LP MVP
    # ========================================================

    def _score_lp_row(row):
        score = 0
        comments = []

        tvl = row.get("tvl_usd")
        volume = row.get("volume_24h")
        days = row.get("days_to_maturity")
        asset_type = row.get("asset_type")

        # ----------------------------------------------------
        # TVL
        # ----------------------------------------------------
        if tvl is not None:
            try:
                tvl = float(tvl)
                if tvl >= 2_000_000:
                    score += 40
                    comments.append("TVL forte")
                elif tvl >= 500_000:
                    score += 25
                    comments.append("TVL correcte")
                elif tvl >= 100_000:
                    score += 10
                    comments.append("TVL moyenne")
                else:
                    comments.append("TVL faible")
            except Exception:
                comments.append("TVL non lisible")

        # ----------------------------------------------------
        # Volume 24h
        # ----------------------------------------------------
        if volume is not None:
            try:
                volume = float(volume)
                if volume >= 1_000_000:
                    score += 35
                    comments.append("volume solide")
                elif volume >= 250_000:
                    score += 20
                    comments.append("volume correct")
                elif volume >= 50_000:
                    score += 10
                    comments.append("volume modeste")
                else:
                    comments.append("volume faible")
            except Exception:
                comments.append("volume non lisible")

        # ----------------------------------------------------
        # Maturité
        # ----------------------------------------------------
        if days is not None:
            try:
                days = int(float(days))
                if 14 <= days <= 180:
                    score += 20
                    comments.append("fenêtre correcte")
                elif 7 <= days <= 13:
                    score += 5
                    comments.append("maturité courte")
                elif days > 180:
                    score += 10
                    comments.append("maturité longue")
                elif days < 7:
                    comments.append("trop proche maturité")
            except Exception:
                comments.append("maturité non lisible")

        # ----------------------------------------------------
        # Bonus stable
        # ----------------------------------------------------
        if asset_type == "stable":
            score += 5
            comments.append("profil stable")

        # ----------------------------------------------------
        # Signal final
        # ----------------------------------------------------
        if score >= 70:
            signal = "🟢 Bon LP"
        elif score >= 40:
            signal = "🟡 LP correct"
        else:
            signal = "🔴 LP faible"

        return score, signal, " | ".join(comments)

    lp_results = filtered.apply(_score_lp_row, axis=1, result_type="expand")
    lp_results.columns = ["lp_score", "lp_signal", "lp_comment"]

    filtered["lp_score"] = lp_results["lp_score"]
    filtered["lp_signal"] = lp_results["lp_signal"]
    filtered["lp_comment"] = lp_results["lp_comment"]

    # Tri principal
    filtered = filtered.sort_values(by="pt_score", ascending=False)

    # Colonnes formatées pour affichage lisible
    filtered["tvl_display"] = filtered["tvl_usd"].apply(_format_usd_short)
    filtered["volume_display"] = filtered["volume_24h"].apply(_format_usd_short)

    display_cols = [
        "asset_symbol",
        "chain",
        "asset_type",
        "implied_apy",
        "underlying_apy",
        "maturity_date",
        "days_to_maturity",
        "tvl_display",
        "volume_display",
        "pt_score",
        "pt_signal",
        "pt_comment",
        "lp_score",
        "lp_signal",
        "lp_comment",
        "lp_max_boosted_apy",
        "points",
    ]

    safe_cols = [c for c in display_cols if c in filtered.columns]

    st.caption(f"{len(filtered)} marché(x) affiché(s).")

    display_df = filtered.loc[:, safe_cols].rename(columns={
        "tvl_display": "TVL",
        "volume_display": "Volume 24h",
        "pt_score": "PT Score",
        "pt_signal": "PT Signal",
        "pt_comment": "PT Comment",
        "lp_score": "LP Score",
        "lp_signal": "LP Signal",
        "lp_comment": "LP Comment",
        "lp_max_boosted_apy": "LP Boost %",
        "points": "Points",
    })

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )
    # ========================================================
    # Fiche détail marché
    # ========================================================
    st.divider()
    st.markdown("### 🔎 Fiche détail marché")

    if not filtered.empty and "asset_symbol" in filtered.columns:
        # On construit des choix lisibles : "asset_symbol | chain"
        # (évite l'ambiguïté si un actif existe sur plusieurs chaînes)
        choice_map = {}
        for _, r in filtered.iterrows():
            sym = str(r.get("asset_symbol") or "?")
            ch = str(r.get("chain") or "?")
            label = f"{sym} | {ch}"
            choice_map[label] = r

        selected_detail = st.selectbox(
            "Voir le détail de…",
            ["—"] + list(choice_map.keys()),
            key="market_scan_detail_select",
        )

        if selected_detail and selected_detail != "—":
            row = choice_map[selected_detail]

            # --- En-tête : titre + signaux ---
            st.markdown(f"#### {row.get('asset_symbol')} — {row.get('chain')}")

            c1, c2, c3 = st.columns(3)
            with c1:
                apy_val = row.get("implied_apy")
                st.metric("APY implicite", f"{apy_val:.2f}%" if apy_val is not None else "—")
                st.metric("TVL", _format_usd_short(row.get("tvl_usd")))
            with c2:
                st.metric("Maturité", str(row.get("maturity_date")) if row.get("maturity_date") else "—")
                st.metric("Jours restants", str(row.get("days_to_maturity")) if row.get("days_to_maturity") is not None else "—")
            with c3:
                boost = row.get("lp_max_boosted_apy")
                st.metric("LP Boost", f"{boost:.2f}%" if boost is not None else "—")
                st.metric("Volume 24h", _format_usd_short(row.get("volume_24h")))

            # --- Infos textuelles ---
            info_lines = []
            if row.get("points"):
                info_lines.append(f"**🎁 Points / Airdrop :** {row.get('points')}")
            if row.get("info_conversion"):
                info_lines.append(f"**🔄 Taux de conversion :** {row.get('info_conversion')}")
            if row.get("info_protocols"):
                info_lines.append(f"**🔗 Protocoles :** {row.get('info_protocols')}")
            if info_lines:
                st.markdown("  \n".join(info_lines))

            if row.get("info_description"):
                st.markdown(f"**Description :** {row.get('info_description')}")

            if row.get("info_risk"):
                st.warning(f"⚠️ **Risque :** {row.get('info_risk')}")

            if row.get("info_quirks"):
                st.info(f"💡 **Particularités :** {row.get('info_quirks')}")

            if row.get("info_deposit_url"):
                st.link_button("🌐 Ouvrir sur le protocole", row.get("info_deposit_url"))