"""
venus_utils.py
VENUS VORTEX — Utility condivise

Centralizza funzioni duplicate in più moduli:
- load_json / save_json
- parse_date (ordinamento cronologico)
- sort_history_by_date

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

# Range concorsi 2026
YEAR_2026_MIN = 1
YEAR_2026_MAX = 999  # Lasciato ampio per flessibilità (attualmente arriva a 150)

# Range hard somma sestine (SuperEnalotto)
SUM_HARD_MIN = 240
SUM_HARD_MAX = 310


def get_year_from_concorso(concorso):
    """Ritorna l'anno (2025 o 2026) dal numero di concorso."""
    if not isinstance(concorso, int):
        return None
    if YEAR_2025_MIN <= concorso <= YEAR_2025_MAX:
        return 2025
    if 1 <= concorso <= 150:  # Range attuale 2026
        return 2026
    return None


def get_concorso_key(concorso, data=None):
    """
    Ritorna una chiave univoca (anno, concorso) per evitare
    collisioni tra 2025 e 2026 con stesso numero.
    """
    year = get_year_from_concorso(concorso)
    if year is None and data:
        year = parse_date(data)[0] or None
    return (year, concorso)
