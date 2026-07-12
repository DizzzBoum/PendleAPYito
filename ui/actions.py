import streamlit as st
from datetime import datetime, timezone
from services.actions_service import ActionsService
from adapters.pendle_execution import get_available_stables
from adapters.kits_bridge import estimate_gas_indicative, HAS_RPC_KIT, HAS_PRICE_KIT

from adapters.txkit_bridge import (
    kit_status,
    prepare_and_simulate,
    confirm_and_execute,
)
# ============================================================
# Helpers affichage
# ============================================================

def _fmt_pct(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "-"


def _fmt_usd(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f} $"
    except Exception:
        return "-"



# new_str
@st.cache_data(ttl=30)
def _cached_gas_indicative(chain: str, action_type: str) -> dict:
    """Estimation gas — 1 seul appel RPC+prix toutes les 30s par (chain, action)."""
    return estimate_gas_indicative(chain=chain, action_type=action_type)


def _render_gas_hint(chain: str, action_type: str) -> None:
    """Estimation gas indicative (lecture seule, mode deeplink).

    Appelle estimate_gas_indicative() depuis kits_bridge via cache 30s.
    Silencieux si les kits sont absents.
    Encapsulé ici pour garder render_actions() lisible.
    """
    if not (HAS_RPC_KIT and HAS_PRICE_KIT):
        return

    gas = _cached_gas_indicative(chain=chain, action_type=action_type)

    if not gas["available"]:
        reason = gas.get("reason") or "—"
        st.caption(f"⛽ Gas estimé : indisponible ({reason})")
        return

    fee_fmt = _fmt_gas_fee(gas["fee_usd"])
    token_price_fmt = _fmt_token_price(gas["gas_token_price_usd"])
    # Indicateur si le gwei vient d'un fallback statique (chaîne hors CHAIN_ENV_MAP)
    is_fallback = gas.get("reason") == "fallback_static_gwei"
    suffix = "  ·  *gwei statique*" if is_fallback else ""

    detail = (
        f"{gas['gas_units'] // 1000}k gas"
        f" · {gas['gas_price_gwei']:.3f} gwei"
        f" · {gas['gas_token']} {token_price_fmt}"
        f"{suffix}"
    )

    if gas["exceeds_max"]:
        st.error(
            f"⛽ Gas estimé : {fee_fmt} — ⚠️ dépasse le garde-fou"
            f" ${gas['max_usd']:.2f}  ·  {detail}"
        )
    else:
        st.success(f"⛽ Gas estimé : {fee_fmt}  ·  {detail}")


# new_str
def _fmt_gas_fee(v: float) -> str:
    """Format USD pour un coût gas, adapté aux très petits montants.

    Adapte la précision selon l'ordre de grandeur pour que
    $0,0000114 ne s'affiche pas comme $0,0000.
    Séparateur décimal : virgule (cohérent avec cockpit_bar).
    """
    if v >= 0.01:
        return f"${v:.4f}".replace(".", ",")
    elif v >= 0.000001:
        return f"${v:.6f}".replace(".", ",")
    else:
        return "< $0,000001"


def _fmt_token_price(v: float) -> str:
    """Format prix du gas token natif dans le détail gas.

    Adapte la précision : $0 ne doit jamais s'afficher pour
    un token dont le prix est $0,09.
    """
    if v >= 100:
        return f"${v:.0f}"
    elif v >= 1:
        return f"${v:.2f}".replace(".", ",")
    elif v >= 0.0001:
        return f"${v:.4f}".replace(".", ",")
    else:
        return f"${v:.6f}".replace(".", ",")


# ============================================================
# Render main
# ============================================================
def render_actions():
    st.subheader("Actions manuelles")

    service = ActionsService()
    markets = service.get_market_options()

    if not markets:
        st.warning("Aucun market disponible. Fais d'abord un refresh du Market Scan.")
        return

    st.caption("Préparation manuelle uniquement — aucune exécution automatique.")

    # ============================================================
    # Controls
    # ============================================================

    c1, c2 = st.columns(2)

    with c1:
        selected_action = st.selectbox(
            "Type d'action",
            ["Buy PT", "Add LP", "Claim rewards"],
            key="actions_select_action",
        )

    with c2:
        only_active = st.checkbox(
            "Afficher seulement les marchés actifs",
            value=True,
            key="actions_only_active_checkbox",
        )

    # ============================================================
    # Filtrage marchés
    # ============================================================

    available_markets = markets

    # Filtre chaîne (propre à l'onglet Actions)
    all_chains = sorted({m.get("chain") for m in markets if m.get("chain")})
    chain_choice = st.selectbox(
        "Chaîne",
        ["ALL"] + all_chains,
        key="actions_chain_filter",
    )
    if chain_choice != "ALL":
        available_markets = [
            m for m in available_markets if m.get("chain") == chain_choice
        ]

    if only_active:
        available_markets = [
            m for m in available_markets if m.get("is_active", True)
        ]

    if not available_markets:
        st.info("Aucun marché actif disponible avec le filtre actuel.")
        return

    # ============================================================
    # Sélection market
    # ============================================================
    # Tri par APY décroissant — meilleur marché en premier
    available_markets.sort(key=lambda m: m.get("implied_apy") or 0, reverse=True)

    labels = [m["label"] for m in available_markets]

    selected_label = st.selectbox(
        "Choisir un marché",
        labels,
        key="actions_select_market",
    )

    selected_market = next(
        m for m in available_markets if m["label"] == selected_label
    )

    # ============================================================
    # Token d'entrée
    # ============================================================

    market_chain = selected_market.get("chain", "ethereum")
    available_stables = get_available_stables(market_chain)

    selected_stable = st.selectbox(
        "Token d'entrée",
        available_stables,
        key="actions_stable_token",
    )

    # ============================================================
    # Montant
    # ============================================================

    amount = st.number_input(
        "Montant",
        min_value=0.0,
        value=10.0,
        step=100.0,
        key="actions_amount",
    )

    # ============================================================
    # Infos marché
    # ============================================================

    st.divider()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Actif", selected_market.get("asset_symbol") or "-")

    with k2:
        st.metric("APY", _fmt_pct(selected_market.get("implied_apy")))

    with k3:
        st.metric("Maturité", selected_market.get("maturity_date") or "-")

    with k4:
        d = selected_market.get("days_to_maturity")
        st.metric("Jours restants", f"{int(d)}" if d is not None else "-")

    # ============================================================
    # Signal intelligent (à partir du market sélectionné)
    # ============================================================

    try:
        apy = float(selected_market.get("implied_apy")) if selected_market.get("implied_apy") is not None else None
    except Exception:
        apy = None

    try:
        days = int(float(selected_market.get("days_to_maturity"))) if selected_market.get(
            "days_to_maturity") is not None else None
    except Exception:
        days = None

    try:
        tvl = float(selected_market.get("tvl_usd")) if selected_market.get("tvl_usd") is not None else None
    except Exception:
        tvl = None

    signal_messages = []

    if apy is not None and apy > 15:
        signal_messages.append("🟢 APY élevé")

    if tvl is not None and tvl < 20000:
        signal_messages.append("🟡 TVL faible")

    if days is not None and days < 30:
        signal_messages.append("🟠 maturité proche")

    for msg in signal_messages:
        st.warning(msg)

    # ============================================================
    # Warning maturité (important pour Pendle)
    # ============================================================

    if days is not None and days < 14:
        st.error("⚠️ Très proche maturité → stratégie YT risquée")
    elif days is not None and days < 30:
        st.warning("⚠️ Maturité proche → attention au timing")

    # ============================================================
    # Préparation action
    # ============================================================

    st.divider()

    prepared = service.prepare_action(
        market=selected_market,
        action_type=selected_action,
        amount=amount,
        stable_token=selected_stable,
    )

    # ============================================================
    # Estimation gas indicative
    # ============================================================

    _render_gas_hint(
        chain=prepared.get("chain", "ethereum"),
        action_type=selected_action,
    )

    # ============================================================
    # Bouton sauvegarde ordre
    # ============================================================

    import json
    from pathlib import Path

    ORDERS_FILE = Path("data/orders.json")

    if st.button("📌 Ajouter à Orders"):

        if ORDERS_FILE.exists():
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                orders = json.load(f)
        else:
            orders = []

        existing_nums = set()
        for o in orders:
            oid = o.get("order_id", "")
            if oid.startswith("ord_"):
                try:
                    existing_nums.add(int(oid.split("_")[1]))
                except Exception:
                    pass
        next_num = max(existing_nums, default=0) + 1

        prepared["order_id"] = f"ord_{next_num:03d}"
        prepared["status"] = "OPEN"
        prepared["created_at"] = datetime.now(timezone.utc).isoformat()

        orders.append(prepared)

        with open(ORDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(orders, f, indent=2, ensure_ascii=False)

        st.toast(f"Ordre {prepared['order_id']} ajouté ✅", icon="📌")
        st.rerun()

    # ============================================================
    # Résumé + Payload
    # ============================================================

    left, right = st.columns([1, 1])

    with left:
        st.markdown("### Résumé")

        st.write(f"**Action :** {prepared['action_type']}")
        st.write(f"**Market :** {prepared['market_name']}")
        st.write(f"**Chaîne :** {prepared['chain']}")
        st.write(f"**Actif :** {prepared['asset_symbol']}")
        st.write(f"**Montant :** {prepared['amount']:,.2f}")

        st.write(f"**TVL :** {_fmt_usd(prepared['tvl_usd'])}")
        st.write(f"**Volume 24h :** {_fmt_usd(prepared['volume_24h'])}")

        st.write(f"**Mode :** {prepared['execution_mode']}")

    with right:
        st.markdown("### Payload préparé")
        st.json(prepared)

    # ============================================================
    # Info
    # ============================================================

    st.info(
        "V1 : cette page prépare seulement l'action.\n"
        "Le branchement transaction / SDK viendra après."
    )
# ============================================================
    # Deeplink Pendle + validation TransactionKit
    # ============================================================
    from adapters.pendle_url import build_pendle_url, action_supports_kit

    st.divider()
    st.markdown("### 🔗 Ouvrir sur Pendle")

    pendle_url = build_pendle_url(prepared)

    # Montant à recopier (Pendle ne pré-remplit pas le montant via URL)
    st.info(f"💵 Montant à saisir manuellement sur Pendle : **{prepared.get('amount')} {prepared.get('stable_token', '')}**")

    kit_ok, kit_err = kit_status()
    supports_kit = action_supports_kit(prepared)

    if not supports_kit:
        # Add LP / Buy YT : pas de validation kit, deeplink direct
        st.caption("Validation TransactionKit non disponible pour ce type d'action — deeplink direct.")
        if pendle_url:
            st.link_button("🌐 Ouvrir sur Pendle", pendle_url)
        else:
            st.warning("Impossible de construire l'URL (market_id manquant).")
    else:
        # Buy PT : validation kit AVANT d'autoriser le deeplink
        st.markdown("#### 🔐 Vérification TransactionKit (dry-run)")

        if not kit_ok:
            st.caption(
                f"transaction_kit non disponible ({kit_err}). "
                "Le deeplink reste accessible ci-dessous sans vérification."
            )
            if pendle_url:
                st.link_button("🌐 Ouvrir sur Pendle", pendle_url)
        else:
            if st.button("🔧 Vérifier via TransactionKit"):
                res = prepare_and_simulate(prepared)
                st.session_state["txkit_result"] = res

            res = st.session_state.get("txkit_result")
            if res is not None:
                if res.validation_errors:
                    st.error("❌ Validation refusée :")
                    for err in res.validation_errors:
                        st.write(f"- {err}")
                    st.caption("Le deeplink reste possible mais le kit a signalé un point d'attention.")
                    if pendle_url:
                        st.link_button("🌐 Ouvrir sur Pendle (malgré l'alerte)", pendle_url)
                elif res.ok:
                    st.success("✅ Vérifié par TransactionKit (entrée allowlistée, router vérifié).")
                    if res.checklist_text:
                        with st.expander("Voir la checklist"):
                            st.code(res.checklist_text)
                    if pendle_url:
                        st.link_button("🌐 Ouvrir sur Pendle", pendle_url)
                else:
                    st.warning(res.message)
                    if pendle_url:
                        st.link_button("🌐 Ouvrir sur Pendle", pendle_url)