import requests


class PendleAPI:
    """
    Client HTTP minimal pour l'API Pendle.

    Objectif V1 :
    - récupérer les marchés
    - récupérer les positions d'un wallet
    - garder une couche simple et propre
    - éviter que l'UI parle directement à l'API
    """

    def __init__(self, base_url: str = "https://api-v2.pendle.finance/core", timeout: int = 20):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_all_markets(
            self,
            limit: int = 100,
            skip: int = 0,
            chain_id: int = None,
    ) -> dict:
        """
        Récupère une page de marchés Pendle.
        skip : offset (0 = début). Paramètre natif de l'API Pendle v2.
        chain_id optionnel : filtre côté API sur une chaîne spécifique.
        Sans chain_id, l'API renvoie toutes les chaînes (cross-chain).
        """
        url = f"{self.base_url}/v2/markets/all"
        params = {
            "limit": limit,
            "skip": skip,
        }

        if chain_id is not None:
            params["chainId"] = chain_id

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_all_pages(
        self,
        chain_id: int = None,
        page_size: int = 100,
        max_pages: int = 10,
    ) -> list[dict]:
        """
        Récupère tous les marchés en parcourant les pages via skip/limit.

        Sans chain_id : cross-chain, toutes les chaînes en une passe.
        Avec chain_id : limité à la chaîne spécifiée.

        Critère d'arrêt : la page retourne moins de page_size résultats.
        Déduplication sur address en filet de sécurité.
        max_pages : garde-fou anti-boucle infinie.
        """
        all_items = []
        seen: set = set()
        for page in range(max_pages):
            skip = page * page_size
            raw = self.get_all_markets(limit=page_size, skip=skip, chain_id=chain_id)
            items = raw.get("results", [])
            for item in items:
                addr = item.get("address")
                if addr and addr not in seen:
                    seen.add(addr)
                    all_items.append(item)
            if len(items) < page_size:
                break  # dernière page atteinte
        return all_items

    def get_user_positions(self, address: str, chain_id: int = None) -> dict:
        """
        Récupère les positions d'un wallet sur Pendle.

        Endpoint typique : /v1/users/{address}/all-positions
        ou /v2/sdk/{chainId}/balances/{address}

        Note : vérifier la doc officielle Pendle API pour l'endpoint exact.
        https://api-v2.pendle.finance/core/docs
        """
        # Tentative endpoint v1 (à ajuster selon doc réelle)
        url = f"{self.base_url}/v1/users/{address}/all-positions"

        params = {}
        if chain_id is not None:
            params["chainId"] = chain_id

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def healthcheck(self) -> bool:
        try:
            _ = self.get_all_markets(limit=1, page=1)
            return True
        except Exception:
            return False