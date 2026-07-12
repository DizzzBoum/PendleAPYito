import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# Stablecoin addresses per chain — priority order: Base, BNB, HyperEVM, Arbitrum, Optimism, Polygon, Ethereum
TOKEN_ADDRESSES_BY_CHAIN: Dict[int, Dict[str, str]] = {
    8453: {  # Base
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
        "DAI":  "0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb",
        "USDe": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
    },
    56: {  # BNB — note: USDT is 18 decimals on this chain
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
        "DAI":  "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3",
    },
    999: {},  # HyperEVM — no public stable addresses yet; add when known
    42161: {  # Arbitrum
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
        "DAI":  "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "USDe": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
    },
    10: {  # Optimism
        "USDC": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
        "USDT": "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
        "DAI":  "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
        "USDe": "0x5d3a1Ff2b6BAb83b63cd9AD0787074081a52ef34",
    },
    137: {  # Polygon
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
        "DAI":  "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063",
    },
    1: {  # Ethereum
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "DAI":  "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        "USDe": "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3",
    },
}

# Standard ERC-20 decimals per stablecoin symbol
STABLE_DECIMALS: Dict[str, int] = {
    "USDC": 6,
    "USDT": 6,
    "DAI":  18,
    "USDe": 18,
}

# Per-chain overrides where a token's decimals differ from STABLE_DECIMALS
_STABLE_DECIMALS_OVERRIDES: Dict[int, Dict[str, int]] = {
    56: {"USDT": 18},  # BNB Chain USDT uses 18 decimals
}


def get_available_stables(chain_name: str) -> list:
    """Returns stablecoin symbols available for a given chain name."""
    _name_to_id = {
        "ethereum": 1, "optimism": 10, "bnb": 56, "polygon": 137,
        "base": 8453, "arbitrum": 42161, "hyperevm": 999,
    }
    chain_id = _name_to_id.get((chain_name or "").lower(), 1)
    tokens = TOKEN_ADDRESSES_BY_CHAIN.get(chain_id, {})
    return list(tokens.keys()) or ["USDC"]


class PendleExecutionAdapter:
    """
    Adapter pour préparer les transactions Pendle via l'API Hosted SDK.
    Format de sortie normalisé compatible avec le moteur commun futur.
    """

    def __init__(self, base_url: str = "https://api-v2.pendle.finance/core", timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.chain_map = {
            "ethereum": 1,
            "optimism": 10,
            "bnb": 56,
            "polygon": 137,
            "arbitrum": 42161,
            "base": 8453,
            "hyperevm": 999,
        }

        self._market_cache = {}

    # ============================================================
    # HELPERS
    # ============================================================

    def _get_chain_id(self, chain: str) -> int:
        return self.chain_map.get(chain.lower(), 1)

    def _extract_address(self, value):
        if isinstance(value, dict):
            return value.get("address") or value.get("addr")
        return value if isinstance(value, str) else None

    def _extract_decimals(self, value, default=18):
        if isinstance(value, dict):
            return value.get("decimals", default)
        return default

    def _format_amount(self, raw_amount, decimals=18):
        try:
            amount = float(raw_amount) / (10 ** int(decimals))
            if amount >= 1000:
                return f"{amount:,.2f}"
            elif amount >= 1:
                return f"{amount:.4f}"
            else:
                return f"{amount:.6f}"
        except Exception:
            return str(raw_amount)

    def _get_market_metadata(self, market_address: str, chain: str) -> Dict[str, Any]:
        cache_key = f"{chain}_{market_address}"

        if cache_key in self._market_cache:
            return self._market_cache[cache_key]

        chain_id = self._get_chain_id(chain)
        url = f"{self.base_url}/v1/{chain_id}/markets/{market_address}"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            metadata = {
                "pt_address": self._extract_address(data.get("pt")),
                "yt_address": self._extract_address(data.get("yt")),
                "sy_address": self._extract_address(data.get("sy")),
                "underlying_address": self._extract_address(data.get("underlyingAsset")),
                "pt_decimals": self._extract_decimals(data.get("pt"), 18),
                "underlying_decimals": self._extract_decimals(data.get("underlyingAsset"), 18),
                "lp_decimals": 18,
                "found": True,
            }

            self._market_cache[cache_key] = metadata
            return metadata
        except Exception as e:
            return {
                "found": False,
                "error": str(e),
                "pt_address": None,
                "underlying_address": None,
                "pt_decimals": 18,
                "underlying_decimals": 18,
                "lp_decimals": 18,
            }

    def _build_pendle_url(self, action_type: str, market_address: str, chain: str,
                          amount_display: Optional[str] = None) -> str:
        """
        Construit un deeplink Pendle.finance.
        Utilise le format universel /trade/markets/ qui fonctionne pour tout type d'action.
        """
        chain_slug = chain.lower()
        action_lower = action_type.lower()

        base_url = f"https://app.pendle.finance/trade/markets/{market_address}"

        # Buy/Sell PT : view=pt
        if "pt" in action_lower:
            url = f"{base_url}/swap?view=pt&chain={chain_slug}"
            if "sell" in action_lower or "vendre" in action_lower:
                url += "&order=sell"
            if amount_display:
                url += f"&inputAmount={amount_display}"
            return url

        # Add LP / Remove LP : on pointe vers le market, l'utilisateur clique sur Pool
        if "lp" in action_lower:
            url = f"{base_url}?chain={chain_slug}"
            if amount_display:
                url += f"&inputAmount={amount_display}"
            return url

        # Fallback générique
        url = f"{base_url}?chain={chain_slug}"
        if amount_display:
            url += f"&inputAmount={amount_display}"
        return url

    def _normalize_response(
            self,
            raw: Dict[str, Any],
            action_type: str,
            chain: str,
            market_address: str,
            token_in_decimals: int = 18,
            token_out_decimals: int = 18,
            amount_in_user: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            tx = raw.get("transaction", {}) or raw.get("tx", {})
            data = raw.get("data", {})

            amount_in_raw = str(data.get("amountTokenIn") or data.get("amountIn") or amount_in_user or "0")
            amount_out_raw = str(
                data.get("amountOut")
                or data.get("amountPtOut")
                or data.get("amountLpOut")
                or "0"
            )

            amount_in_display = self._format_amount(amount_in_raw, token_in_decimals)
            amount_out_display = self._format_amount(amount_out_raw, token_out_decimals)

            pendle_url = self._build_pendle_url(
                action_type=action_type,
                market_address=market_address,
                chain=chain,
                amount_display=amount_in_display.replace(",", ""),
            )

            return {
                "status": "ready",
                "action_type": action_type,
                "chain": chain,
                "chain_id": self._get_chain_id(chain),
                "market_address": market_address,
                "amount_in_raw": amount_in_raw,
                "amount_out_raw": amount_out_raw,
                "amount_in_display": amount_in_display,
                "amount_out_display": amount_out_display,
                "token_in_decimals": token_in_decimals,
                "token_out_decimals": token_out_decimals,
                "price_impact": float(data.get("priceImpact", 0)),
                "gas_estimate": int(tx.get("gasLimit", 0) or 0),
                "tx_data": {
                    "to": tx.get("to", ""),
                    "data": tx.get("data", ""),
                    "value": tx.get("value", "0"),
                    "gasLimit": tx.get("gasLimit", "0"),
                },
                "pendle_url": pendle_url,
                "additional_info": {
                    "implied_apy_before": data.get("impliedApy"),
                    "implied_apy_after": data.get("impliedApyAfter"),
                    "effective_apy": data.get("effectiveApy"),
                },
                "prepared_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            return {
                "status": "error",
                "action_type": action_type,
                "error": str(e),
                "raw_response": raw,
            }

    # ============================================================
    # BUY PT
    # ============================================================

    def prepare_buy_pt(self, market_address, chain, token_in, amount_in, receiver, slippage=0.01):
        chain_id = self._get_chain_id(chain)
        metadata = self._get_market_metadata(market_address, chain)

        if not metadata.get("pt_address"):
            return {
                "status": "error",
                "action_type": "Buy PT",
                "error": f"Adresse PT introuvable pour market {market_address}",
                "pendle_url": self._build_pendle_url("Buy PT", market_address, chain),
            }

        url = f"{self.base_url}/v2/sdk/{chain_id}/markets/{market_address}/swap"
        params = {
            "receiver": receiver,
            "slippage": slippage,
            "tokenIn": token_in,
            "tokenOut": metadata["pt_address"],
            "amountIn": amount_in,
            "enableAggregator": "true",
            "aggregators": "kyberswap,odos",
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._normalize_response(
                raw=response.json(),
                action_type="Buy PT",
                chain=chain,
                market_address=market_address,
                token_in_decimals=6,
                token_out_decimals=metadata["pt_decimals"],
                amount_in_user=amount_in,
            )
        except Exception as e:
            return {
                "status": "error",
                "action_type": "Buy PT",
                "error": str(e),
                "pendle_url": self._build_pendle_url("Buy PT", market_address, chain),
            }

    # ============================================================
    # SELL PT
    # ============================================================

    def prepare_sell_pt(self, market_address, chain, amount_pt_in, token_out, receiver, slippage=0.01):
        chain_id = self._get_chain_id(chain)
        metadata = self._get_market_metadata(market_address, chain)

        if not metadata.get("pt_address"):
            return {
                "status": "error",
                "action_type": "Sell PT",
                "error": f"Adresse PT introuvable pour market {market_address}",
                "pendle_url": self._build_pendle_url("Sell PT", market_address, chain),
            }

        url = f"{self.base_url}/v2/sdk/{chain_id}/markets/{market_address}/swap"
        params = {
            "receiver": receiver,
            "slippage": slippage,
            "tokenIn": metadata["pt_address"],
            "tokenOut": token_out,
            "amountIn": amount_pt_in,
            "enableAggregator": "true",
            "aggregators": "kyberswap,odos",
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._normalize_response(
                raw=response.json(),
                action_type="Sell PT",
                chain=chain,
                market_address=market_address,
                token_in_decimals=metadata["pt_decimals"],
                token_out_decimals=6,
                amount_in_user=amount_pt_in,
            )
        except Exception as e:
            return {
                "status": "error",
                "action_type": "Sell PT",
                "error": str(e),
                "pendle_url": self._build_pendle_url("Sell PT", market_address, chain),
            }

    # ============================================================
    # ADD LIQUIDITY
    # ============================================================

    def prepare_add_liquidity(self, market_address, chain, token_in, amount_in, receiver, slippage=0.01, keep_yt=False):
        chain_id = self._get_chain_id(chain)
        metadata = self._get_market_metadata(market_address, chain)

        url = f"{self.base_url}/v2/sdk/{chain_id}/markets/{market_address}/add-liquidity"
        params = {
            "receiver": receiver,
            "slippage": slippage,
            "tokenIn": token_in,
            "amountIn": amount_in,
            "enableAggregator": "true",
            "zpi": str(keep_yt).lower(),
            "aggregators": "kyberswap,odos",
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._normalize_response(
                raw=response.json(),
                action_type="Add LP",
                chain=chain,
                market_address=market_address,
                token_in_decimals=6,
                token_out_decimals=metadata["lp_decimals"],
                amount_in_user=amount_in,
            )
        except Exception as e:
            # Fallback : essayer avec l'underlying du market
            if metadata.get("underlying_address") and metadata["underlying_address"].lower() != token_in.lower():
                try:
                    params["tokenIn"] = metadata["underlying_address"]
                    user_amount = float(amount_in) / (10 ** 6)
                    new_amount = str(int(user_amount * (10 ** metadata["underlying_decimals"])))
                    params["amountIn"] = new_amount

                    response = requests.get(url, params=params, timeout=self.timeout)
                    response.raise_for_status()
                    return self._normalize_response(
                        raw=response.json(),
                        action_type="Add LP",
                        chain=chain,
                        market_address=market_address,
                        token_in_decimals=metadata["underlying_decimals"],
                        token_out_decimals=metadata["lp_decimals"],
                        amount_in_user=new_amount,
                    )
                except Exception as e2:
                    return {
                        "status": "error",
                        "action_type": "Add LP",
                        "error": f"USDC: {e} | Underlying: {e2}",
                        "pendle_url": self._build_pendle_url("Add LP", market_address, chain),
                    }

            return {
                "status": "error",
                "action_type": "Add LP",
                "error": str(e),
                "pendle_url": self._build_pendle_url("Add LP", market_address, chain),
            }

    # ============================================================
    # REMOVE LIQUIDITY
    # ============================================================

    def prepare_remove_liquidity(self, market_address, chain, lp_amount, token_out, receiver, slippage=0.01):
        chain_id = self._get_chain_id(chain)
        metadata = self._get_market_metadata(market_address, chain)

        url = f"{self.base_url}/v2/sdk/{chain_id}/markets/{market_address}/remove-liquidity"
        params = {
            "receiver": receiver,
            "slippage": slippage,
            "tokenOut": token_out,
            "amountLpIn": lp_amount,
            "enableAggregator": "true",
            "aggregators": "kyberswap,odos",
        }

        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return self._normalize_response(
                raw=response.json(),
                action_type="Remove LP",
                chain=chain,
                market_address=market_address,
                token_in_decimals=metadata["lp_decimals"],
                token_out_decimals=6,
                amount_in_user=lp_amount,
            )
        except Exception as e:
            return {
                "status": "error",
                "action_type": "Remove LP",
                "error": str(e),
                "pendle_url": self._build_pendle_url("Remove LP", market_address, chain),
            }

    # ============================================================
    # PREPARE FROM ORDER (routage avec slippage)
    # ============================================================

    def prepare_from_order(self, order: Dict[str, Any], receiver: str, slippage: float = 0.01) -> Dict[str, Any]:
        action_type = order.get("action_type", "").lower()
        market_id = order.get("market_id")
        chain = order.get("chain", "ethereum")
        amount = order.get("amount", 0)

        chain_id = self._get_chain_id(chain)
        stable_token = order.get("stable_token", "USDC")
        chain_tokens = TOKEN_ADDRESSES_BY_CHAIN.get(chain_id, {})
        token_stable = chain_tokens.get(stable_token)
        if token_stable is None:
            available = list(chain_tokens.keys()) or ["aucun"]
            return {
                "status": "error",
                "action_type": action_type,
                "error": f"{stable_token} non disponible sur {chain} (chain_id={chain_id}). Disponibles : {available}",
                "pendle_url": self._build_pendle_url(action_type, market_id, chain),
            }

        stable_decimals = _STABLE_DECIMALS_OVERRIDES.get(chain_id, {}).get(
            stable_token, STABLE_DECIMALS.get(stable_token, 6)
        )
        amount_stable_wei = str(int(float(amount) * (10 ** stable_decimals)))

        # Vendre PT
        if ("sell" in action_type or "vendre" in action_type) and "pt" in action_type:
            metadata = self._get_market_metadata(market_id, chain)
            pt_decimals = metadata.get("pt_decimals", 18)
            amount_pt_wei = str(int(float(amount) * (10 ** pt_decimals)))

            return self.prepare_sell_pt(
                market_address=market_id,
                chain=chain,
                amount_pt_in=amount_pt_wei,
                token_out=token_stable,
                receiver=receiver,
                slippage=slippage,
            )

        # Buy PT
        if "buy" in action_type and "pt" in action_type:
            return self.prepare_buy_pt(
                market_address=market_id,
                chain=chain,
                token_in=token_stable,
                amount_in=amount_stable_wei,
                receiver=receiver,
                slippage=slippage,
            )

        # Add LP
        if ("add" in action_type or "ajouter" in action_type) and "lp" in action_type:
            return self.prepare_add_liquidity(
                market_address=market_id,
                chain=chain,
                token_in=token_stable,
                amount_in=amount_stable_wei,
                receiver=receiver,
                slippage=slippage,
            )

        # Remove LP
        if ("remove" in action_type or "retirer" in action_type) and "lp" in action_type:
            metadata = self._get_market_metadata(market_id, chain)
            lp_decimals = metadata.get("lp_decimals", 18)
            amount_lp_wei = str(int(float(amount) * (10 ** lp_decimals)))

            return self.prepare_remove_liquidity(
                market_address=market_id,
                chain=chain,
                lp_amount=amount_lp_wei,
                token_out=token_stable,
                receiver=receiver,
                slippage=slippage,
            )

        return {
            "status": "error",
            "error": f"Type d'action non supporté : {action_type}",
            "action_type": action_type,
            "pendle_url": self._build_pendle_url(action_type, market_id, chain),
        }