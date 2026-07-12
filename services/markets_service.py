import json
from datetime import datetime, date
from pathlib import Path

from adapters.pendle_api import PendleAPI
from config import DATA_DIR


class MarketsService:
    """Transforme les données brutes Pendle en dataset propre pour l'UI."""

    def __init__(self):
        self.api = PendleAPI()
        self.output_file = DATA_DIR / "markets.json"

    def refresh_markets(self) -> list[dict]:
        raw = self.api.get_all_markets(limit=100, page=1)

        # Selon la réponse réelle, il faudra adapter la clé results/items/data
        items = raw.get("results", []) or raw.get("markets", []) or raw.get("data", [])

        normalized = []
        today = date.today()

        for item in items:
            maturity_str = item.get("maturity") or item.get("expiry")
            maturity_date = None
            days_to_maturity = None

            if maturity_str:
                try:
                    maturity_date = datetime.fromisoformat(
                        maturity_str.replace("Z", "+00:00")
                    ).date()
                    days_to_maturity = (maturity_date - today).days
                except Exception:
                    maturity_date = None
                    days_to_maturity = None

            normalized.append({
                "market_id": item.get("address") or item.get("marketAddress"),
                "market_name": item.get("name") or item.get("marketName"),
                "chain": item.get("chain") or item.get("chainName"),
                "asset_symbol": item.get("underlyingSymbol") or item.get("symbol"),
                "asset_type": self._detect_asset_type(item),
                "implied_apy": self._safe_float(item.get("impliedApy")),
                "underlying_apy": self._safe_float(item.get("underlyingApy")),
                "maturity_date": str(maturity_date) if maturity_date else None,
                "days_to_maturity": days_to_maturity,
                "tvl_usd": self._safe_float(item.get("tvl")),
                "volume_24h": self._safe_float(item.get("volume24h")),
                "is_active": item.get("isActive", True),
            })

        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.output_file.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

        return normalized

    def _detect_asset_type(self, item: dict) -> str:
        symbol = (item.get("underlyingSymbol") or item.get("symbol") or "").lower()
        if any(x in symbol for x in ["usdc", "usdt", "dai", "usde", "fdusd", "susde"]):
            return "stable"
        if "eth" in symbol or "weth" in symbol:
            return "eth"
        if "btc" in symbol or "wbtc" in symbol:
            return "btc"
        return "other"

    @staticmethod
    def _safe_float(value):
        try:
            return float(value) if value is not None else None
        except Exception:
            return None