# ui/_theme.py
# Thème global partagé entre les bots (PendleAPYito reprend le thème AnyLiqBot)
# parents[1] = racine du projet PendleAPYito (charge PendleAPYito/.env si présent)

from __future__ import annotations

import os
import streamlit as st

from pathlib import Path

try:
    from dotenv import load_dotenv
    # ui/_theme.py -> parents[1] = AnyLiqBot/
    load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)
except Exception:
    pass


def apply_theme() -> None:


    """
    Theme global AnyLiqBot:
    - Full width
    - Background "deep navy + neon"
    - Chips / LED (Patch 2: Laser trim + halo/fumée)
    - Couleurs via .env (optionnel)
    """

    # Base accents (customisables via .env)
    ACCENT = os.getenv("UI_ACCENT", "rgba(56,189,248,0.95)")              # running / cyan
    ACCENT_SOFT = os.getenv("UI_ACCENT_SOFT", "rgba(56,189,248,0.12)")

    VIOLET = os.getenv("UI_VIOLET", "rgba(168,85,247,0.92)")
    VIOLET_SOFT = os.getenv("UI_VIOLET_SOFT", "rgba(168,85,247,0.16)")

    YELLOW = os.getenv("UI_YELLOW", "rgba(245,158,11,0.92)")              # skipped
    YELLOW_SOFT = os.getenv("UI_YELLOW_SOFT", "rgba(245,158,11,0.18)")

    PINK = os.getenv("UI_PINK", "rgba(244,114,182,0.92)")                 # error / rose
    PINK_SOFT = os.getenv("UI_PINK_SOFT", "rgba(244,114,182,0.18)")

    st.markdown(
        f"""
<style>
/* =========================
   GLOBAL FULL WIDTH
========================= */
.block-container {{
  max-width: 100% !important;
  padding-left: 2.2rem !important;
  padding-right: 2.2rem !important;
  padding-top: 1.2rem !important;
}}

/* =========================
   GLOBAL BACKGROUND
========================= */
[data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(1200px 520px at 20% 10%, {ACCENT_SOFT}, rgba(2,6,23,0.0)),
    radial-gradient(1200px 520px at 72% 8%, {VIOLET_SOFT}, rgba(2,6,23,0.0));
}}

/* JSON blocks: fond translucide harmonisé (Payload préparé / Détail brut) */
[data-testid="stJson"] {{
  background: rgba(255,255,255,0.03) !important;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.06);
  padding: 10px 14px;
}}
/* Conteneur interne du JSON (le carré noir par défaut) */
[data-testid="stJson"] > div,
[data-testid="stJson"] pre {{
  background: transparent !important;
}}

/* =========================================================
   AnyLiqBot — Chips (Patch 2: Laser trim) + LED
   Classes attendues:
   - .any-chip (ou .chip)
   - .any-led (ou .chipDot)
   - états: .is-running / .is-skipped / .is-error / .is-off
   ========================================================= */
:root {{
  --neo-blue: {ACCENT};
  --neo-blue-soft: {ACCENT_SOFT};

  --neo-vio: {VIOLET};
  --neo-vio-soft: {VIOLET_SOFT};

  --neo-yel: {YELLOW};
  --neo-yel-soft: {YELLOW_SOFT};

  --neo-pink: {PINK};
  --neo-pink-soft: {PINK_SOFT};
}}

.any-chip, .chip {{
  --c: var(--neo-blue);
  --csoft: var(--neo-blue-soft);

  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 10px;

  padding: 9px 14px;
  border-radius: 999px;

  border: 1px solid rgba(148,163,184,0.18);
  background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));

  box-shadow:
    0 12px 28px rgba(0,0,0,0.30),
    0 0 24px rgba(56,189,248,0.10);

  backdrop-filter: blur(12px);
  overflow: visible;
}}

/* “fumée/halo” derrière (discret, comme 3_status avant) */
.any-chip::before, .chip::before {{
  content: "";
  position: absolute;
  inset: -14px -16px;
  border-radius: 999px;
  background: radial-gradient(240px 120px at 20% 50%, color-mix(in srgb, var(--c) 15%, transparent), transparent 35%);
  filter: blur(14px);
  opacity: 0.50;
  z-index: -1;
}}

/* Liseré “laser trim” (haut gauche + bas droite) */
.any-chip::after, .chip::after {{
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 999px;
  pointer-events: none;

  background:
    linear-gradient(90deg,
      color-mix(in srgb, var(--c) 0%, transparent) 0%,
      color-mix(in srgb, var(--c) 55%, transparent) 18%,
      transparent 45%),
    linear-gradient(270deg,
      color-mix(in srgb, var(--c) 0%, transparent) 0%,
      color-mix(in srgb, var(--c) 45%, transparent) 16%,
      transparent 42%);

  opacity: 0.85;
  mask:
    linear-gradient(#000, #000) content-box,
    linear-gradient(#000, #000);
  -webkit-mask:
    linear-gradient(#000, #000) content-box,
    linear-gradient(#000, #000);
  padding: 1px; /* épaisseur du liseré */
  box-sizing: border-box;
}}

/* Texte interne (si tu utilises span.label/muted) */
.any-chip .label, .chip .chipLabel {{
  font-weight: 950;
  letter-spacing: 0.5px;
  color: rgba(255,255,255,0.92);
}}
.any-chip .muted, .chip .chipValue, .chip .muted {{
  color: rgba(226,232,240,0.70);
  font-weight: 800;
  font-size: 12px;
}}

/* LED dot */
.any-led, .chipDot {{
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: rgba(148,163,184,0.35);
  box-shadow: 0 0 0 4px rgba(255,255,255,0.05);
}}

.any-led.on, .chipDot.on {{
  background: var(--c);
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--c) 12%, transparent),
    0 0 18px color-mix(in srgb, var(--c) 45%, transparent),
    0 0 46px color-mix(in srgb, var(--c) 29%, transparent);
}}

/* ---------- chip states -> set color vars ---------- */
.any-chip.is-running, .chip.is-running {{
  --c: var(--neo-blue);
  --csoft: var(--neo-blue-soft);
}}

.any-chip.is-skipped, .chip.is-skipped {{
  --c: var(--neo-yel);
  --csoft: var(--neo-yel-soft);
}}

.any-chip.is-error, .chip.is-error {{
  --c: var(--neo-pink);
  --csoft: var(--neo-pink-soft);
}}

.any-chip.is-rate, .chip.is-rate {{
  --c: var(--neo-vio);
  --csoft: var(--neo-vio-soft);
}}

.any-chip.is-off, .chip.is-off {{
  --c: rgba(148,163,184,0.55);
  --csoft: rgba(148,163,184,0.10);
}}


/* Hover (juste un micro bonus, pas violent) */
.any-chip:hover, .chip:hover {{
  transform: translateY(-0.5px);
  box-shadow:
    0 14px 34px rgba(0,0,0,0.34),
    0 0 28px color-mix(in srgb, var(--c) 14%, transparent);
  transition: 120ms ease;
}}
</style>
""",
        unsafe_allow_html=True,
    )
