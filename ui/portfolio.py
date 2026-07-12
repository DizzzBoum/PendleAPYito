import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from services.portfolio_service import PortfolioService

ORDERS_FILE = Path("data/orders.json")
MARKETS_FILE = Path("data/markets.json")


def render_portfolio():
    st.subheader("Portfolio")

    service = PortfolioService()

    # ============================================================
    # Wallet address input
    # ============================================================

    col1, col2 = st.columns([3, 1])

    with col1:
        wallet_address = st.text_input(
            "Adresse wallet (laisser vide pour mock)",
            value="",
            placeholder="0x...",
            key="portfolio_wallet_address",
        )

    with col2:
        st.caption(" ")
        if st.button("Charger positions", width="stretch"):
            st.toast("Chargement des positions..." if wallet_address else "Mode mock")
            st.rerun()

    # ============================================================
    # DATA
    # ============================================================

    data = service.compute(address=wallet_address if wallet_address.strip() else None)
    df = pd.DataFrame(data)

    if df.empty:
        st.info("Aucune position.")
        return

    # ============================================================
    # KPIs
    # ============================================================

    total_value = df["value_usd"].sum()
    total_pnl = df["pnl_usd"].sum()
    avg_pnl_pct = df["pnl_pct"].mean()

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Valeur totale", f"{total_value:,.2f} $")

    with k2:
        st.metric("PnL total", f"{total_pnl:,.2f} $")

    with k3:
        st.metric("PnL moyen (%)", f"{avg_pnl_pct:.2f}%")

    with k4:
        st.metric("Positions", len(df))

    st.divider()

    # ============================================================
    # CLEAN TYPES
    # ============================================================

    numeric_cols = ["value_usd", "pnl_usd", "pnl_pct", "days_to_maturity"]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ============================================================
    # TAGS
    # ============================================================

    def tag(row):
        tags = []

        if row.get("days_to_maturity") is not None and row["days_to_maturity"] <= 30:
            tags.append("maturité proche")

        if row.get("pnl_pct") is not None and row["pnl_pct"] >= 10:
            tags.append("bon profit")

        if row.get("pnl_pct") is not None and row["pnl_pct"] <= -5:
            tags.append("perte")

        return " | ".join(tags)

    df["signal"] = df.apply(tag, axis=1)

    # ============================================================
    # DISPLAY
    # ============================================================

    display_cols = [
        "position_type",
        "market_name",
        "chain",
        "quantity",
        "value_usd",
        "pnl_usd",
        "pnl_pct",
        "maturity_date",
        "days_to_maturity",
        "signal",
    ]

    safe_cols = [c for c in display_cols if c in df.columns]

    st.dataframe(
        df.loc[:, safe_cols].sort_values(by="pnl_pct", ascending=False),
        width="stretch",
        hide_index=True,
    )

    # ============================================================
    # ACTIONS RAPIDES
    # ============================================================

    st.divider()
    st.subheader("Actions rapides")

    # Build position options
    position_options = [""]
    position_map = {}

    for idx, row in df.iterrows():
        pos_type = row.get("position_type", "?")
        market = row.get("market_name", "?")
        chain = row.get("chain", "?")
        qty = row.get("quantity", 0)
        pnl_pct = row.get("pnl_pct", 0)

        label = f"{pos_type} | {market} | {chain} | {qty:.1f} qty | {pnl_pct:+.2f}% PnL"
        position_options.append(label)
        position_map[label] = row.to_dict()

    selected_label = st.selectbox(
        "Position à trader",
        position_options,
        key="portfolio_quick_action_position",
    )

    if selected_label and selected_label != "":
        position = position_map[selected_label]

        # ============================================================
        # Context card
        # ============================================================

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Maturité", position.get("maturity_date", "-"))

        with col2:
            days = position.get("days_to_maturity")
            st.metric("Jours restants", f"{int(days)}" if days is not None else "-")

        with col3:
            pnl_usd = position.get("pnl_usd", 0)
            pnl_pct = position.get("pnl_pct", 0)
            st.metric("PnL actuel", f"{pnl_usd:+,.2f} $ ({pnl_pct:+.2f}%)")

        st.divider()

        # ============================================================
        # Action form
        # ============================================================

        col_action, col_amount = st.columns(2)

        with col_action:
            action_type = st.selectbox(
                "Type d'action",
                ["Vendre PT", "Vendre YT", "Retirer LP", "Ajouter LP"],
                key="portfolio_action_type",
            )

        with col_amount:
            amount = st.number_input(
                "Montant",
                min_value=0.0,
                value=10.0,
                step=10.0,
                key="portfolio_action_amount",
            )

        # ============================================================
        # Create order button
        # ============================================================

        if st.button("🚀 Créer l'ordre", key="portfolio_create_order"):
            # Try to find market_id
            market_id = position.get("market_id")

            if not market_id:
                # Try to find in markets cache by name + chain
                if MARKETS_FILE.exists():
                    try:
                        markets = json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
                        for m in markets:
                            if (m.get("market_name") == position.get("market_name")
                                    and m.get("chain") == position.get("chain")):
                                market_id = m.get("market_id")
                                break
                    except Exception:
                        pass

            if not market_id:
                st.error(
                    f"Impossible de créer l'ordre : le marché '{position.get('market_name')}' "
                    f"sur {position.get('chain')} est introuvable dans le cache. "
                    f"Fais un refresh du Market Scan sur cette chaîne d'abord."
                )
            else:
                # Build order
                order = {
                    "action_type": action_type,
                    "amount": amount,
                    "market_id": market_id,
                    "market_name": position.get("market_name"),
                    "chain": position.get("chain"),
                    "asset_symbol": position.get("market_name"),
                    "asset_type": "unknown",
                    "maturity_date": position.get("maturity_date"),
                    "days_to_maturity": position.get("days_to_maturity"),
                    "stable_token": "USDC",
                    "execution_mode": "manual_only",
                    "source": "portfolio",
                }

                # Save order (same logic as actions.py)
                if ORDERS_FILE.exists():
                    with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                        orders = json.load(f)
                else:
                    orders = []

                # Generate ID
                existing_nums = set()
                for o in orders:
                    oid = o.get("order_id", "")
                    if oid.startswith("ord_"):
                        try:
                            existing_nums.add(int(oid.split("_")[1]))
                        except Exception:
                            pass
                next_num = max(existing_nums, default=0) + 1

                order["order_id"] = f"ord_{next_num:03d}"
                order["status"] = "OPEN"
                order["created_at"] = datetime.now(timezone.utc).isoformat()

                orders.append(order)

                with open(ORDERS_FILE, "w", encoding="utf-8") as f:
                    json.dump(orders, f, indent=2, ensure_ascii=False)

                st.toast(f"Ordre {order['order_id']} créé depuis Portfolio ✅", icon="🚀")
                st.rerun()