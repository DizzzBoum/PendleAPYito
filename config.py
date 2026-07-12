from pathlib import Path

# ============================================================
# Configuration globale du projet PendleAPYitot
# ============================================================

# Dossier racine du projet
BASE_DIR = Path(__file__).resolve().parent

# Dossier local pour stocker les JSON de cache / travail
DATA_DIR = BASE_DIR / "data"

# Base URL officielle Pendle
# La documentation Pendle indique que le Hosted SDK et les endpoints
# principaux s'appuient sur https://api-v2.pendle.finance/core
PENDLE_API_BASE = "https://api-v2.pendle.finance/core"

# Timeout HTTP par défaut
DEFAULT_TIMEOUT = 20

# Paramètres UX / filtrage V1
DEFAULT_MIN_TVL_USD = 0
DEFAULT_MIN_APY = 0.0

# Fichier local du market scan
MARKETS_FILE = DATA_DIR / "markets.json"