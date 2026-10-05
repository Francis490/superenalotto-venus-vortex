"""
venus_utils.py
VENUS VORTEX — Utility condivise.

FIX (2026-10-05 v3):
- load_json e save_json ora sono importati da core_io.py (modulo condiviso
  tra Aurora e Venus). Vedi CORE_SYNC.md.
  Il file resta retrocompatibile: gli altri moduli che fanno
  `from venus_utils import load_json, save_json` continuano a funzionare.

FIX (2026-10-05 v2):
- get_year_from_concorso parametrico via YEAR_RANGES.

FIX (2026-10-05 v1):
- Aggiunta get_year_from_date per il fallback dalla data.
"""
import os
from datetime import datetime

# Core condiviso: importiamo load_json/save_json da core_io.
# Gli altri moduli possono continuare a importarli da venus_utils.
from core_io import load_json, save_json, load_json_strict


# ==========================================
# DATE
# ==========================================
def parse_date(date_str):
    """
    Converte 'DD/MM/YYYY' in tupla (YYYY, MM, DD) per ordinamento.
    Ritorna (0, 0, 0) se non valida.
    """
    try:
        dt = datetime.strptime(str(date_str), "%d/%m/%Y")
        return (dt.year, dt.month, dt.day)
    except Exception:
        return (0, 0, 0)


def is_valid_date(date_str):
    """Ritorna True se la stringa è in formato DD/MM/YYYY valido."""
    return parse_date(date_str) != (0, 0, 0)


def sort_history_by_date(history):
    """
    Ordina una lista di entry (con campo 'data') cronologicamente.
    Usa parse_date per gestire correttamente anni diversi (2025/2026).
    """
    return sorted(history, key=lambda x: parse_date(x.get("data", "")))


# ==========================================
# COSTANTI DI DOMINIO
# ==========================================
# Offset per concorsi 2025 (evita collisione con 2026)
YEAR_2025_OFFSET = 1000
YEAR_2025_MIN = 1001
YEAR_2025_MAX = 1208

# Range concorsi 2026 (aperto a 999 per non dover essere toccato ogni anno)
YEAR_2026_MIN = 1
YEAR_2026_MAX = 999

# Mappa anno -> (min, max).
YEAR_RANGES = {
    2025: (YEAR_2025_MIN, YEAR_2025_MAX),
    2026: (YEAR_2026_MIN, YEAR_2026_MAX),
}

# Range hard somma sestine (SuperEnalotto)
SUM_HARD_MIN = 240
SUM_HARD_MAX = 310


# ==========================================
# ANNO / CONCORSO
# ==========================================
def get_year_from_concorso(concorso, ranges=None):
    """
    Ritorna l'anno (2025, 2026, ...) dal numero di concorso.

    FIX (2026-10-05): prima era hardcoded a `1 <= concorso <= 150`.
    Ora usa YEAR_RANGES, ordinato dal range più alto al più basso per
    evitare collisioni (es. 1001 deve essere 2025, non 2026).
    """
    if not isinstance(concorso, int):
        return None

    ranges = ranges or YEAR_RANGES

    sorted_years = sorted(ranges.keys(), reverse=True)
    for year in sorted_years:
        lo, hi = ranges[year]
        if lo <= concorso <= hi:
            return year
    return None


def get_year_from_date(date_str):
    """Ritorna l'anno da una data DD/MM/YYYY, o None."""
    y, m, d = parse_date(date_str)
    return y if y > 0 else None


def get_concorso_key(concorso, data=None):
    """
    Ritorna una chiave univoca (anno, concorso) per evitare
    collisioni tra 2025 e 2026 con stesso numero.
    """
    year_concorso = get_year_from_concorso(concorso)
    year_data = get_year_from_date(data) if data else None

    if year_concorso and year_data and year_concorso != year_data:
        print(f"[!] Discrepanza anno per concorso {concorso}: "
              f"range→{year_concorso}, data→{year_data}. Uso la data.")
        return (year_data, concorso)

    if year_data:
        return (year_data, concorso)
    if year_concorso:
        return (year_concorso, concorso)

    print(f"[!] Impossibile dedurre anno per concorso {concorso} "
          f"(data='{data}'). Uso (None, {concorso}).")
    return (None, concorso)
