"""
adapters/txkit_bridge.py

Pont OPTIONNEL entre PendleAPYito (cockpit Streamlit) et la librairie
partagée transaction_kit.

Principe :
- L'UI ne parle JAMAIS directement au kit. Elle passe par ce pont.
- L'import du kit est protégé : si transaction_kit n'est pas installé,
  le cockpit continue de fonctionner normalement (KIT_AVAILABLE = False).
- Tout reste en dry-run V0 : mode=DRY_RUN, signer=None,
  safety_profile par défaut "v0_manual_dry_run".

Périmètre actuel : uniquement "Buy PT" = approve (USDC -> Router) + swap
(USDC -> PT). LP / Claim seront ajoutés plus tard (tests + ADR dédié).
"""

from __future__ import annotations

# ============================================================
# Import optionnel du kit
# ============================================================
KIT_AVAILABLE = False
KIT_IMPORT_ERROR = None

try:
    from transaction_kit import (
        TransactionPlan,
        PlanMode,
        validate,
        simulate,
        checklist,
        execute,
        logger,
    )
    KIT_AVAILABLE = True
except Exception as e:  # ImportError ou autre souci d'installation
    KIT_IMPORT_ERROR = str(e)


# ============================================================
# Constantes Pendle
# ============================================================
# Router Pendle V4 — adresse réelle vérifiée (cache verified_contracts.yaml du kit).
# Tous les swaps PT/YT Pendle passent par ce routeur (confirmé).
PENDLE_ROUTER_V4 = "0x888888888889758F76e7103c6CbF23ABbF58F946"


# ============================================================
# Résultat structuré renvoyé à l'UI
# ============================================================
class BridgeResult:
    """Conteneur simple pour remonter l'état du pipeline à Streamlit."""

    def __init__(self):
        self.ok = False
        self.stage = None            # "validate" | "simulate" | "confirm" | "execute"
        self.validation_errors = []  # list[str]
        self.simulation_result = None
        self.checklist_text = ""
        self.execution_result = None
        self.plan = None             # le TransactionPlan pour les étapes suivantes
        self.message = ""


def kit_status() -> tuple[bool, str | None]:
    """Permet à l'UI de savoir si le kit est dispo (et pourquoi pas, le cas échéant)."""
    return KIT_AVAILABLE, KIT_IMPORT_ERROR


# ============================================================
# Construction du plan "Buy PT"
# ============================================================
def build_buy_pt_plan(prepared: dict) -> "TransactionPlan":
    """
    Traduit un ordre PendleAPYito (dict 'prepared' issu de ActionsService)
    en TransactionPlan transaction_kit.

    Buy PT = 2 steps :
      1. approve  : USDC -> Router V4 (exact_amount, jamais d'infinite approve)
      2. swap     : USDC -> PT (asset_symbol), via Router V4

    Le market_id PendleAPYito va dans params.market (non validé regex côté kit).
    Le contract du step est TOUJOURS le Router V4.
    """
    if not KIT_AVAILABLE:
        raise RuntimeError("transaction_kit non disponible.")

    chain = prepared.get("chain") or "ethereum"
    stable = prepared.get("stable_token") or "USDC"
    asset_symbol = prepared.get("asset_symbol") or "PT"
    amount = float(prepared.get("amount") or 0)
    market_id = prepared.get("market_id") or "0x0000000000000000000000000000000000000000"

    plan = TransactionPlan(
        bot_origin="pendle_apyito",
        description=f"Buy PT {asset_symbol} ({chain}) — {amount} {stable}",
        mode=PlanMode.DRY_RUN,  # V0 : toujours dry_run
        # safety_profile="v0_manual_dry_run" est le défaut
    )

    # Step 1 — approve (exact_amount)
    # amount_usd=0 : un approve n'est PAS un mouvement de fonds, il ne doit pas
    # compter dans le "Total USD estimé". Correctif temporaire côté pont en
    # attendant que le kit ignore nativement les steps approve dans le total
    # (sujet ADR + tests côté transaction_kit).
    plan.add_step(
        action="approve",
        protocol="pendle",
        chain=chain,
        token_in=stable,
        amount=amount,
        amount_usd=0.0,
        contract=PENDLE_ROUTER_V4,
        params={
            "spender": PENDLE_ROUTER_V4,
            "approval_type": "exact_amount",
        },
    )

    # Step 2 — swap USDC -> PT
    plan.add_step(
        action="swap",
        protocol="pendle",
        chain=chain,
        token_in=stable,
        token_out=asset_symbol,
        amount=amount,
        amount_usd=amount,
        contract=PENDLE_ROUTER_V4,
        params={
            "market": market_id,
            "slippage_bps": 50,
        },
    )

    return plan


# ============================================================
# Étape 1 : validate + simulate + génération checklist
# ============================================================
def prepare_and_simulate(prepared: dict) -> BridgeResult:
    """
    Construit le plan, le valide, le simule (dry-run) et génère la checklist.
    Ne confirme PAS et n'exécute PAS : c'est un acte humain séparé.
    """
    result = BridgeResult()

    if not KIT_AVAILABLE:
        result.message = f"transaction_kit indisponible : {KIT_IMPORT_ERROR}"
        return result

    # Construction
    try:
        plan = build_buy_pt_plan(prepared)
    except Exception as e:
        result.stage = "build"
        result.message = f"Erreur construction du plan : {e}"
        return result

    # Validation
    plan = validate(plan)
    result.plan = plan
    result.stage = "validate"

    val_errors = getattr(plan, "validation_errors", None) or []
    if val_errors:
        result.validation_errors = [str(x) for x in val_errors]
        result.message = "La validation a rejeté le plan."
        return result

    # Simulation (dry-run)
    try:
        plan = simulate(plan)
        result.plan = plan
        result.stage = "simulate"
        result.simulation_result = getattr(plan, "simulation_result", None)
    except Exception as e:
        result.message = f"Erreur simulation : {e}"
        return result

    # Checklist (texte généré par le kit)
    try:
        result.checklist_text = checklist.generate_checklist(plan)
    except Exception as e:
        result.checklist_text = f"(checklist indisponible : {e})"

    result.ok = True
    result.message = "Plan validé et simulé (dry-run). Checklist prête à confirmer."
    return result


# ============================================================
# Étape 2 : confirm + execute (dry-run) + log
# ============================================================
def confirm_and_execute(plan) -> BridgeResult:
    """
    Confirme la checklist, exécute en dry-run (signer=None) et journalise.
    Aucune transaction réelle : execute.py refuse tout broadcast en V0.
    """
    result = BridgeResult()
    result.plan = plan

    if not KIT_AVAILABLE:
        result.message = f"transaction_kit indisponible : {KIT_IMPORT_ERROR}"
        return result

    # Confirmation checklist
    try:
        plan = checklist.confirm(plan)
        result.plan = plan
        result.stage = "confirm"
    except Exception as e:
        result.message = f"Erreur confirmation checklist : {e}"
        return result

    # Exécution dry-run (jamais de signer en V0)
    try:
        plan = execute(plan, signer=None)
        result.plan = plan
        result.stage = "execute"
        result.execution_result = getattr(plan, "execution_result", None)
    except Exception as e:
        result.message = f"Erreur exécution (dry-run) : {e}"
        return result

    # Log
    try:
        logger.log_plan_full(plan, event="pendle_buy_pt_dry_run")
    except Exception as e:
        result.message = f"Plan exécuté (dry-run) mais log échoué : {e}"
        result.ok = True
        return result

    result.ok = True
    result.message = "Plan exécuté en dry-run et journalisé dans ./tx_logs/."
    return result
