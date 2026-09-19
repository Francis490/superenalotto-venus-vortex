"""
build_history_2026.py
VENUS VORTEX — Validator storico 2026 (v2)

Cambio di paradigma (2026-09-19):
- `venus_history.json` è la FONTE DI VERITÀ per i dati storici.
- Questo script NON contiene più dati hardcoded (erano stale e divergevano dal JSON).
- Scopo attuale: verificare che il database contenga tutti i 150 concorsi 2026.

Per il bootstrap di un nuovo anno (es. 2027), usare `import_external_history.py`
con un file `external_history.json` popolato esternamente.

Uso:
    python build_history_2026.py
"""
import json
import os
import sys
from datetime import datetime
from collections import Counter


HISTORY_FILE = "venus_history.json"

# Range atteso per il 2026
EXPECTED_2026_MIN = 1
EXPECTED_2026_MAX = 150
EXPECTED_2026_COUNT = 150

# Range atteso per il 2025 (con offset +1000)
EXPECTED_2025_MIN = 1001
EXPECTED_2025_MAX = 1208
EXPECTED_2025_COUNT = 208


def parse_date(date_str):
    """Ritorna (YYYY, MM, DD) per ordinamento cronologico."""
    try:
        dt = datetime.strptime(str(date_str), "%d/%m/%Y")
        return (dt.year, dt.month, dt.day)
    except Exception:
        return (0, 0, 0)


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura {HISTORY_FILE}: {e}")
            sys.exit(1)
    print(f"[!] File {HISTORY_FILE} non trovato.")
    sys.exit(1)


def get_concorsi_2026(history):
    """Ritorna i concorsi 2026 (1-999), escludendo 2025 (1001+)."""
    ids = set()
    for item in history:
        c = item.get("concorso")
        if isinstance(c, int) and EXPECTED_2026_MIN <= c <= 999:
            ids.add(c)
    return ids


def get_concorsi_2025(history):
    """Ritorna i concorsi 2025 (offset +1000)."""
    ids = set()
    for item in history:
        c = item.get("concorso")
        if isinstance(c, int) and EXPECTED_2025_MIN <= c <= EXPECTED_2025_MAX:
            ids.add(c)
    return ids


def check_duplicates(history):
    """Ritorna la lista di concorsi duplicati (con contatore)."""
    counter = Counter(
        item.get("concorso") for item in history
        if isinstance(item.get("concorso"), int)
    )
    return {c: n for c, n in counter.items() if n > 1}


def check_invalid_entries(history):
    """Ritorna entry con struttura non valida."""
    invalid = []
    for item in history:
        c = item.get("concorso")
        comb = item.get("combinazione", [])
        data = item.get("data", "")

        errors = []
        if not isinstance(c, int) or c <= 0:
            errors.append("concorso non valido")
        if not isinstance(comb, list) or len(comb) != 6:
            errors.append("combinazione non è una lista di 6 numeri")
        elif not all(isinstance(n, int) and 1 <= n <= 90 for n in comb):
            errors.append("combinazione contiene numeri fuori range 1-90")
        if not parse_date(data):
            errors.append(f"data non valida: '{data}'")

        if errors:
            invalid.append({
                "concorso": c,
                "data": data,
                "errors": errors,
            })
    return invalid


def main():
    print("=== BUILD HISTORY 2026 — VALIDATOR ===")
    print()

    history = load_history()
    print(f"[*] {HISTORY_FILE}: {len(history)} entry totali")
    print()

    # Analisi 2026
    ids_2026 = get_concorsi_2026(history)
    expected_2026 = set(range(EXPECTED_2026_MIN, EXPECTED_2026_MAX + 1))
    missing_2026 = sorted(expected_2026 - ids_2026)
    extra_2026 = sorted(ids_2026 - expected_2026)

    print(f"📅 Anno 2026:")
    print(f"    • Attesi:     {EXPECTED_2026_COUNT} concorsi (1-{EXPECTED_2026_MAX})")
    print(f"    • Presenti:   {len(ids_2026)}")
    if missing_2026:
        print(f"    • ❌ MANCANTI: {missing_2026}")
    else:
        print(f"    • ✅ Completo")
    if extra_2026:
        print(f"    • ⚠️  FUORI RANGE: {extra_2026}")

    # Analisi 2025
    ids_2025 = get_concorsi_2025(history)
    expected_2025 = set(range(EXPECTED_2025_MIN, EXPECTED_2025_MAX + 1))
    missing_2025 = sorted(expected_2025 - ids_2025)
    extra_2025 = sorted(ids_2025 - expected_2025)

    print()
    print(f"📅 Anno 2025 (offset +1000):")
    print(f"    • Attesi:     {EXPECTED_2025_COUNT} concorsi "
          f"({EXPECTED_2025_MIN}-{EXPECTED_2025_MAX})")
    print(f"    • Presenti:   {len(ids_2025)}")
    if missing_2025:
        print(f"    • ❌ MANCANTI: {missing_2025}")
    else:
        print(f"    • ✅ Completo")
    if extra_2025:
        print(f"    • ⚠️  FUORI RANGE: {extra_2025}")

    # Duplicati
    duplicates = check_duplicates(history)
    print()
    if duplicates:
        print(f"⚠️  DUPLICATI: {duplicates}")
    else:
        print(f"✅ Nessun duplicato")

    # Entry invalide
    invalid = check_invalid_entries(history)
    print()
    if invalid:
        print(f"⚠️  ENTRY INVALIDE: {len(invalid)}")
        for item in invalid[:10]:
            print(f"    • concorso {item['concorso']} ({item['data']}): "
                  f"{', '.join(item['errors'])}")
        if len(invalid) > 10:
            print(f"    ... e altre {len(invalid) - 10}")
    else:
        print(f"✅ Nessuna entry invalida")

    # Campo 'sestina' mancante
    missing_sestina = [
        item.get("concorso") for item in history
        if "sestina" not in item
    ]
    print()
    if missing_sestina:
        print(f"⚠️  Entry senza campo 'sestina': {missing_sestina}")
        print(f"    (non bloccante: scraper.py gestisce il fallback)")
    else:
        print(f"✅ Tutte le entry hanno il campo 'sestina'")

    print()
    print("=== COMPLETATO ===")

    # Exit code: 1 se ci sono problemi bloccanti
    if missing_2026 or invalid or duplicates:
        sys.exit(1)


if __name__ == "__main__":
    main()
