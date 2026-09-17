"""
import_external_history.py
Importa estrazioni storiche esterne e le integra con venus_history.json.
Ordina per DATA (non per concorso) per gestire anni diversi.
"""
import json
import os
from datetime import datetime

HISTORY_FILE = "venus_history.json"
EXTERNAL_FILE = "external_history.json"


def parse_date(date_str):
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return (dt.year, dt.month, dt.day)
    except Exception:
        return (0, 0, 0)


def load_json(filepath, default=None):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura {filepath}: {e}")
    return default


def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Salvato: {filepath}")
    except Exception as e:
        print(f"[!] Errore salvataggio {filepath}: {e}")


def validate_entry(entry):
    if not isinstance(entry, dict):
        return False
    concorso = entry.get("concorso")
    comb = entry.get("combinazione", [])
    if not isinstance(concorso, int) or concorso <= 0:
        return False
    if not isinstance(comb, list) or len(comb) != 6:
        return False
    if not all(isinstance(n, int) and 1 <= n <= 90 for n in comb):
        return False
    return True


def main():
    print("=== IMPORT EXTERNAL HISTORY ===")

    external = load_json(EXTERNAL_FILE)
    if not external:
        print(f"[!] {EXTERNAL_FILE} non trovato o vuoto.")
        return

    if not isinstance(external, list):
        print(f"[!] {EXTERNAL_FILE} deve contenere una lista.")
        return

    print(f"[*] Caricate {len(external)} estrazioni esterne")

    valid_external = [e for e in external if validate_entry(e)]
    invalid = len(external) - len(valid_external)
    if invalid > 0:
        print(f"[!] {invalid} non valide (saltate)")
    print(f"[*] Valide: {len(valid_external)}")

    existing = load_json(HISTORY_FILE, [])
    print(f"[*] Storico attuale: {len(existing)} estrazioni")

    existing_ids = {e.get("concorso") for e in existing
                    if isinstance(e.get("concorso"), int)}

    new_entries = [e for e in valid_external
                   if e.get("concorso") not in existing_ids]

    if not new_entries:
        print("[*] Nessuna nuova estrazione.")
        return

    print(f"[+] Aggiungo {len(new_entries)} nuove estrazioni")

    merged = existing + new_entries
    merged.sort(key=lambda x: parse_date(x.get("data", "")))

    ids = [e["concorso"] for e in merged]
    print(f"[*] Range concorsi: {min(ids)} - {max(ids)}")
    print(f"[*] Totale: {len(merged)} estrazioni")

    years = {}
    for e in merged:
        d = e.get("data", "")
        if len(d) >= 4:
            y = d[-4:]
            years[y] = years.get(y, 0) + 1

    print(f"[*] Distribuzione per anno:")
    for y in sorted(years.keys()):
        print(f"    • {y}: {years[y]} concorsi")

    save_json(HISTORY_FILE, merged)
    print("=== COMPLETATO ===")


if __name__ == "__main__":
    main()
