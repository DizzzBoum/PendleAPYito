import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

ORDERS_FILE = Path("data/orders.json")

STATUS_OPEN = "OPEN"
STATUS_SIMULATED = "SIMULATED"
STATUS_CANCELLED = "CANCELLED"


def _calculate_age(created_at_str):
    """Calcule l'âge d'un ordre depuis sa création."""
    if not created_at_str:
        return "-", 0

    try:
        created_dt = datetime.fromisoformat(str(created_at_str).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        age_seconds = (now - created_dt).total_seconds()

        if age_seconds < 3600:  # < 1h
            age_display = f"{int(age_seconds / 60)}m"
        elif age_seconds < 86400:  # < 1 jour
            age_display = f"{int(age_seconds / 3600)}h"
        else:
            days = int(age_seconds / 86400)
            age_display = f"{days}j"
            if days > 3:
                age_display = f"⚠️ {age_display}"

        return age_display, age_seconds
    except Exception:
        return "-", 0


def _fmt_action(order: dict) -> str:
    raw = order.get("action_type") or order.get("side") or "UNKNOWN"
    return str(raw).replace("_", " ").title()


def _fmt_created_at(value):
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


def _fmt_status(status: str) -> str:
    mapping = {
        STATUS_OPEN: "🟢 OPEN",
        STATUS_SIMULATED: "🟡 SIMULATED",
        STATUS_CANCELLED: "🔴 CANCELLED",
    }
    return mapping.get(status, status or STATUS_OPEN)


def render_orders():
    st.title("Orders")
    st.caption("Historique des actions préparées")

    if not ORDERS_FILE.exists():
        st.info("Aucun ordre pour le moment.")
        return

    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            orders = json.load(f)
    except Exception as e:
        st.error(f"Impossible de lire orders.json : {e}")
        return

    if not orders:
        st.info("Aucun ordre.")
        return

    # ============================================================
    # Tri du plus récent au plus ancien
    # ============================================================

    orders = sorted(
        orders,
        key=lambda x: x.get("created_at", ""),
        reverse=True,
    )

    # ============================================================
    # Filtres légers
    # ============================================================

    c1, c2 = st.columns(2)

    with c1:
        available_statuses = ["ALL", STATUS_OPEN, STATUS_SIMULATED, STATUS_CANCELLED]
        selected_status = st.selectbox(
            "Filtrer par statut",
            available_statuses,
            key="orders_filter_status",
        )

    with c2:
        search_text = st.text_input(
            "Recherche market / action",
            value="",
            key="orders_search_text",
        ).strip().lower()

    filtered_orders = orders

    if selected_status != "ALL":
        filtered_orders = [
            o for o in filtered_orders
            if o.get("status", STATUS_OPEN) == selected_status
        ]

    if search_text:
        filtered_orders = [
            o for o in filtered_orders
            if search_text in str(o.get("market_name", "")).lower()
               or search_text in _fmt_action(o).lower()
               or search_text in str(o.get("chain", "")).lower()
        ]

    # ============================================================
    # Nettoyage rapide
    # ============================================================

    old_orders = [o for o in filtered_orders if _calculate_age(o.get("created_at"))[1] > 259200]  # > 3 jours

    if old_orders:
        st.warning(f"⚠️ {len(old_orders)} ordre(s) de plus de 3 jours détecté(s).")

        if st.button(f"🗑️ Supprimer les {len(old_orders)} ordre(s) > 3 jours", key="cleanup_old_orders"):
            updated_orders = [
                o for o in orders
                if _calculate_age(o.get("created_at"))[1] <= 259200
            ]
            with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                json.dump(updated_orders, f, indent=2, ensure_ascii=False)
            st.toast(f"{len(old_orders)} ordre(s) supprimé(s) ✅")
            st.rerun()

    # ============================================================
    # Tableau résumé
    # ============================================================

    rows = []
    for o in filtered_orders:
        age_display, _ = _calculate_age(o.get("created_at"))

        rows.append({
            "ID": o.get("order_id", "-"),
            "Action": _fmt_action(o),
            "Market": o.get("market_name"),
            "Chain": o.get("chain"),
            "Montant": o.get("amount"),
            "Status": _fmt_status(o.get("status", STATUS_OPEN)),
            "Âge": age_display,
            "Créé le": _fmt_created_at(o.get("created_at")),
        })

    st.caption(f"{len(filtered_orders)} ordre(s) affiché(s).")

    summary_df = pd.DataFrame(rows)

    st.dataframe(
        summary_df,
        width="stretch",
        hide_index=True,
    )

    st.divider()
    st.markdown("## Détail brut")

    # ============================================================
    # Champ adresse wallet + slippage pour exécution
    # ============================================================

    st.divider()

    col_wallet, col_slip = st.columns([3, 1])

    with col_wallet:
        wallet_for_execution = st.text_input(
            "Adresse wallet pour exécution",
            value="",
            placeholder="0x...",
            key="orders_wallet_execution",
            help="Nécessaire pour préparer les transactions"
        )

    with col_slip:
        slippage_pct = st.number_input(
            "Slippage (%)",
            min_value=0.001,
            max_value=20.0,
            value=1.0,
            step=0.5,
            key="orders_slippage",
            help="2-5% recommandé pour tokens peu liquides (srRoyAPY, exotiques, etc.)"
        )

    st.caption(
        "ℹ️ Certains markets de l'API peuvent ne pas être affichés sur Pendle.finance (markets récents, peu actifs).")

    # ============================================================
    # Détail par ordre
    # ============================================================

    for order in filtered_orders:
        order_id = order.get("order_id", "unknown_id")
        title_action = _fmt_action(order)
        market_name = order.get("market_name", "unknown_market")
        status = order.get("status", STATUS_OPEN)
        created_at = _fmt_created_at(order.get("created_at"))

        with st.expander(f"{order_id} • {title_action} • {market_name}"):
            st.write(f"**Statut :** {_fmt_status(status)}")
            st.write(f"**Créé le :** {created_at}")
            st.write(f"**Chaîne :** {order.get('chain', '-')}")
            st.write(f"**Montant :** {order.get('amount', '-')}")

            st.json(order)

            # ============================================================
            # Boutons d'action
            # ============================================================

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("❌ Supprimer", key=f"delete_{order_id}", use_container_width=True):
                    updated_orders = [
                        o for o in orders
                        if o.get("order_id") != order_id
                    ]
                    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(updated_orders, f, indent=2, ensure_ascii=False)
                    st.rerun()

            with col2:
                if status != STATUS_SIMULATED and st.button("▶ Simuler", key=f"simulate_{order_id}",
                                                            use_container_width=True):
                    updated_orders = []
                    for o in orders:
                        if o.get("order_id") == order_id:
                            o["status"] = STATUS_SIMULATED
                        updated_orders.append(o)
                    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(updated_orders, f, indent=2, ensure_ascii=False)
                    st.success("Simulation OK ✅")
                    st.rerun()

            with col3:
                if status != STATUS_CANCELLED and st.button("🚫 Annuler", key=f"cancel_{order_id}",
                                                            use_container_width=True):
                    updated_orders = []
                    for o in orders:
                        if o.get("order_id") == order_id:
                            o["status"] = STATUS_CANCELLED
                        updated_orders.append(o)
                    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                        json.dump(updated_orders, f, indent=2, ensure_ascii=False)
                    st.warning("Ordre annulé 🚫")
                    st.rerun()

            with col4:
                if status == STATUS_OPEN:
                    # Lien direct Pendle.finance (pas d'API)
                    from adapters.pendle_execution import PendleExecutionAdapter

                    adapter = PendleExecutionAdapter()
                    action_type = order.get("action_type", "Buy PT")
                    market_id = order.get("market_id", "")
                    chain = order.get("chain", "ethereum")
                    amount = order.get("amount", 10)

                    pendle_url = adapter._build_pendle_url(
                        action_type=action_type,
                        market_address=market_id,
                        chain=chain,
                        amount_display=str(amount),
                    )

                    st.link_button(
                        "🔗 Exécuter sur Pendle",
                        pendle_url,
                        use_container_width=True,
                    )