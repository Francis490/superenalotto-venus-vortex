"""
venus_utils.py
VENUS VORTEX — Utility condivise

Centralizza funzioni duplicate in più moduli:
- load_json / save_json
- parse_date (ordinamento cronologico)
- sort_history_by_date
- get_year_from_concorso / get_concorso_key

FIX (2026-10-05):
- get_year_from_concorso era hardcoded a `1 <= concorso <= 150` per il 2026.
  Con l'avanzare dei concorsi (ora 159+), la funzione ritornava None per
  tutto ciò che superava 150. Sostituito con dict YEAR_RANGES parametrico.
- Aggiunta get_year_from_date per il fallback dalla data.

Cambio architetturale (2026-09-19):
- Creato per ridurre duplicazione (parse_date era copiata in 6+ file)
- Risolve dipendenza circolare backtest_e2e → scraper
"""
import json
import os
from datetime import datetime


# ==========================================
# JSON I/O
# ==========================================
def load_json(filepath, default=None):
    """Carica un file JSON. Ritorna `default` se non esiste o è corrotto."""
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Errore lettura {filepath}: {e}")
        return default


def save_json(filepath, data):
    """Salva un file JSON. Ritorna True se successo, False altrimenti."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Salvato: {filepath}")
        return True
    except Exception as e:
        print(f"[!] Errore salvataggio {filepath}: {e}")
        return False


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

# Mappa anno -> (min, max). Ordine: dal range più alto al più basso,
# così un concorso come 1001 non viene erroneamente classificato come 2026.
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

    :param concorso: numero intero
    :param ranges: dict opzionale {anno: (min, max)} per override.
    :return: anno (int) o None se non classificabile.
    """
    if not isinstance(concorso, int):
        return None

    ranges = ranges or YEAR_RANGES

    # Ordina i range dal più alto al più basso per evitare collisioni
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

    Ordine di risoluzione:
    1. Anno dedotto dal numero di concorso (via YEAR_RANGES)
    2. Fallback: anno dedotto dalla data
    3. Fallback finale: (None, concorso) con warning

    Nota: se anno e data danno risultati diversi, prevale la data
    (più affidabile). Es. concorso 5 con data "2025-..." → anno 2025.
    """
    year_concorso = get_year_from_concorso(concorso)
    year_data = get_year_from_date(data) if data else None

    # Se entrambi disponibili e discordanti → prevale la data
    if year_concorso and year_data and year_concorso != year_data:
        print(f"[!] Discrepanza anno per concorso {concorso}: "
              f"range→{year_concorso}, data→{year_data}. Uso la data.")
        return (year_data, concorso)

    # Se almeno uno è disponibile, usalo
    if year_data:
        return (year_data, concorso)
    if year_concorso:
        return (year_concorso, concorso)

    # Nessuno dei due: warning e fallback
    print(f"[!] Impossibile dedurre anno per concorso {concorso} "
          f"(data='{data}'). Uso (None, {concorso}).")
    return (None, concorso)
