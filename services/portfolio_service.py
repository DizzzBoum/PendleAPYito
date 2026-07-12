import json
from datetime import date, datetime
from pathlib import Path

from adapters.pendle_api import PendleAPI
from config import DATA_DIR, PENDLE_API_BASE, DEFAULT_TIMEOUT


class PortfolioService:
    """
    Service Portfolio V2

    - Lit les positions réelles depuis l'API Pendle si adresse fournie
    - Fallback sur mock local si pas d'adresse
    """

    def __init__(self):
        self.file = DATA_DIR / "portfolio.json"
        self.api = PendleAPI(base_url=PENDLE_API_BASE, timeout=DEFAULT_TIMEOUT)

    # ============================================================
    # FETCH REAL POSITIONS
    # ============================================================
    def fetch_real_positions(self, address: str, chain_id: int = None) -> list[dict]:
        """
        Récupère les positions réelles depuis l'API Pendle.
        Note : endpoint actuellement introuvable, fallback sur mock.
        """
        try:
            raw = self.api.get_user_positions(address, chain_id)
            return self._normalize_positions(raw)
        except Exception:
            # 404 attendu : endpoint non documenté actuellement
            # Fallback silencieux sur mock
            return []

    def _normalize_positions(self, raw: dict) -> list[dict]:
        """
        Normalise la réponse brute de l'API en format interne.

        Adapter selon la structure réelle de l'API Pendle.
        """
        positions = []

        # Structure hypothétique (à ajuster selon la vraie API)
        items = raw.get("positions", []) or raw.get("data", []) or raw.get("results", [])

        today = date.today()

        for item in items:
            position_type = item.get("type", "PT").upper()  # PT, YT, LP
            market_name = item.get("marketName") or item.get("market", {}).get("name")
            chain = item.get("chain") or item.get("chainId")

            # Quantité
            balance = item.get("balance") or item.get("amount") or 0
            quantity = float(balance) if balance else 0

            # Valeur
            value_usd = float(item.get("valueUsd", 0) or 0)

            # Prix d'entrée (peut ne pas être disponible)
            entry_price = float(item.get("entryPrice", 0) or 0)
            current_price = float(item.get("currentPrice", 0) or 0)

            # PnL
            if entry_price > 0 and current_price > 0:
                pnl_usd = (current_price - entry_price) * quantity
                pnl_pct = ((current_price / entry_price) - 1) * 100
            else:
                pnl_usd = 0
                pnl_pct = 0

            # Maturité
            maturity_raw = item.get("maturity") or item.get("expiry")
            maturity_date = None
            days_to_maturity = None

            if maturity_raw:
                try:
                    maturity_date = datetime.fromisoformat(
                        str(maturity_raw).replace("Z", "+00:00")
                    ).date()
                    days_to_maturity = (maturity_date - today).days
                except Exception:
                    pass

            # Market ID
            market_id = item.get("marketId") or item.get("marketAddress")

            positions.append({
                "position_id": f"pos_{len(positions) + 1:03d}",
                "position_type": position_type,
                "market_id": market_id,
                "market_name": market_name,
                "chain": chain,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "value_usd": value_usd,
                "pnl_usd": pnl_usd,
                "pnl_pct": pnl_pct,
                "maturity_date": str(maturity_date) if maturity_date else None,
                "days_to_maturity": days_to_maturity,
            })

        return positions

    # ============================================================
    # MOCK DATA (fallback)
    # ============================================================

    def generate_mock(self):
        today = date.today()

        data = [
            {
                "position_id": "pos_001",
                "position_type": "PT",
                "market_name": "sUSDe Jul 2026",
                "chain": "ethereum",
                "quantity": 10,
                "entry_price": 0.94,
                "current_price": 0.97,
                "maturity_date": "2026-07-25",
            },
        ]

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        return data

    # ============================================================
    # LOAD (priorité : real > cache > mock)
    # ============================================================

    def load(self, address: str = None):
        """
        Charge les positions :
        1. Si adresse fournie → fetch API
        2. Sinon → mock
        """
        if address and address.strip():
            real_positions = self.fetch_real_positions(address.strip())
            if real_positions:
                return real_positions

        # Fallback sur mock
        if not self.file.exists():
            return self.generate_mock()

        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            return self.generate_mock()

    # ============================================================
    # COMPUTE (ajoute calculs sur données chargées)
    # ============================================================

    def compute(self, address: str = None):
        raw = self.load(address)

        today = date.today()
        positions = []

        for p in raw:
            entry = float(p.get("entry_price", 0))
            current = float(p.get("current_price", 0))
            qty = float(p.get("quantity", 0))

            value = p.get("value_usd")
            if value is None:
                value = current * qty

            pnl = p.get("pnl_usd")
            if pnl is None:
                pnl = (current - entry) * qty if entry > 0 else 0

            pnl_pct = p.get("pnl_pct")
            if pnl_pct is None:
                pnl_pct = ((current / entry - 1) * 100) if entry > 0 else 0

            maturity_raw = p.get("maturity_date")
            maturity_date = None
            days = None

            if maturity_raw:
                try:
                    maturity_date = datetime.fromisoformat(str(maturity_raw)).date()
                    days = (maturity_date - today).days
                except Exception:
                    pass

            positions.append({
                **p,
                "value_usd": value,
                "pnl_usd": pnl,
                "pnl_pct": pnl_pct,
                "days_to_maturity": days,
            })

        return positions