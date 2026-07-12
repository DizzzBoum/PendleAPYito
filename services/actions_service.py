import json

from config import DATA_DIR, MARKETS_FILE


class ActionsService:
    """
    Service simple pour préparer des actions manuelles Pendle.
    V1 :
    - lit les marchés depuis le cache local
    - prépare un résumé d'action
    - aucune exécution réelle
    """

    def load_markets(self) -> list[dict]:
        if not MARKETS_FILE.exists():
            return []

        try:
            return json.loads(MARKETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []

    def get_market_options(self) -> list[dict]:
        markets = self.load_markets()

        cleaned = []
        for m in markets:
            market_name = m.get("market_name") or "unknown_market"
            chain = m.get("chain") or "unknown_chain"
            asset_symbol = m.get("asset_symbol") or "unknown_asset"
            implied_apy = m.get("implied_apy")
            tvl_usd = m.get("tvl_usd")
            maturity_date = m.get("maturity_date")
            market_id = m.get("market_id")

            label = f"{market_name} | {chain} | APY {implied_apy:.2f}%" if isinstance(implied_apy, (int, float)) else f"{market_name} | {chain}"

            cleaned.append({
                "label": label,
                "market_id": market_id,
                "market_name": market_name,
                "chain": chain,
                "asset_symbol": asset_symbol,
                "asset_type": m.get("asset_type"),
                "implied_apy": implied_apy,
                "underlying_apy": m.get("underlying_apy"),
                "maturity_date": maturity_date,
                "days_to_maturity": m.get("days_to_maturity"),
                "tvl_usd": tvl_usd,
                "volume_24h": m.get("volume_24h"),
                "is_active": m.get("is_active", True),
            })

        return cleaned

    def prepare_action(
        self,
        market: dict,
        action_type: str,
        amount: float,
        stable_token: str = "USDC",
    ) -> dict:
        """
        Prépare un résumé d'action manuelle.
        Aucune transaction n'est créée en V1.
        """
        return {
            "action_type": action_type,
            "amount": amount,
            "market_id": market.get("market_id"),
            "market_name": market.get("market_name"),
            "chain": market.get("chain"),
            "asset_symbol": market.get("asset_symbol"),
            "asset_type": market.get("asset_type"),
            "implied_apy": market.get("implied_apy"),
            "underlying_apy": market.get("underlying_apy"),
            "maturity_date": market.get("maturity_date"),
            "days_to_maturity": market.get("days_to_maturity"),
            "tvl_usd": market.get("tvl_usd"),
            "volume_24h": market.get("volume_24h"),
            "stable_token": stable_token,
            "execution_mode": "manual_only",
            "status": "prepared",
        }