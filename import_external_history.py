"""
import_external_history.py
Importa estrazioni storiche esterne e le integra con venus_history.json.
Ordina per DATA (non per concorso) per gestire anni diversi.

FIX (2026-09-19):
- #3: merge usa chiave composta (anno, concorso) per evitare collisioni
  tra concorsi 2025 (offset +1000) e 2026 (1-150) con stesso numero.
- Dedup anche all'interno di external_history.json.
- validate_entry: aggiunto check formato data DD/MM/YYYY.
- Import utility condivise da venus_utils.
"""
import os
import sys

from venus_utils import (
    load_json,
    save_json,
    parse_date,
    is_valid_date,
    sort_history_by_date,
    get_concorso_key,
)


HISTORY_FILE = "venus_history.json"
EXTERNAL_FILE = "external_history.json"


def validate_entry(entry):
    """
    Valida una entry di external_history.json.
    Ritorna (ok, error_msg).
    """
    if not isinstance(entry, dict):
        return False, "non è un dict"

    concorso = entry.get("concorso")
    comb = entry.get("combinazione", [])
    data = entry.get("data", "")

    if not isinstance(concorso, int) or concorso <= 0:
        return False, f"concorso non valido: {concorso}"
    if not isinstance(comb, list) or len(comb) != 6:
        return False, f"combinazione non ha 6 numeri (trovati {len(comb) if isinstance(comb, list) else 'N/A'})"
    if not all(isinstance(n, int) and 1 <= n <= 90 for n in comb):
        return False, "combinazione contiene numeri fuori range 1-90"
    if not is_valid_date(data):
        return False, f"data non valida: '{data}'"

    return True, None


def dedup_external(entries):
    """
    Rimuove duplicati all'interno di external_history.json.
    Usa chiave (anno, concorso). In caso di duplicati, tiene il primo.
    """
    seen = {}
    result = []
    duplicates = []

    for e in entries:
        key = get_concorso_key(e.get("concorso"), e.get("data", ""))
        if key in seen:
            duplicates.append(e.get("concorso"))
            continue
        seen[key] = True
        result.append(e)

    return result, duplicates


def build_history_index(history):
    """
    FIX #3: costruisce un indice con chiave (anno, concorso) per
    evitare collisioni tra 2025 e 2026 con stesso numero.
    """
    index = set()
    for e in history:
        c = e.get("concorso")
        if not isinstance(c, int):
            continue
        key = get_concorso_key(c, e.get("data", ""))
        index.add(key)
    return index


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

    # Validazione
    valid_external = []
    invalid_count = 0
    for e in external:
        ok, err = validate_entry(e)
        if ok:
            valid_external.append(e)
        else:
            invalid_count += 1
            if invalid_count <= 5:
                print(f"[!] Entry scartata: {err}")

    if invalid_count > 0:
        print(f"[!] {invalid_count} entry non valide (saltate)")
    print(f"[*] Valide: {len(valid_external)}")

    # FIX: dedup interno al file external
    valid_external, internal_dups = dedup_external(valid_external)
    if internal_dups:
        print(f"[!] {len(internal_dups)} duplicati interni rimossi: "
              f"{internal_dups[:10]}{'...' if len(internal_dups) > 10 else ''}")

    # Carica storico esistente
    existing = load_json(HISTORY_FILE, [])
    print(f"[*] Storico attuale: {len(existing)} estrazioni")

    # FIX #3: indice con chiave (anno, concorso)
    existing_index = build_history_index(existing)

    # Filtra le entry nuove (chiave non presente)
    new_entries = []
    skipped_by_collision = []
    for e in valid_external:
        key = get_concorso_key(e.get("concorso"), e.get("data", ""))
        if key in existing_index:
            skipped_by_collision.append(e.get("concorso"))
            continue
        new_entries.append(e)

    if skipped_by_collision:
        print(f"[*] {len(skipped_by_collision)} entry già presenti "
              f"(skip per collisione)")
        if len(skipped_by_collision) <= 10:
            print(f"    Concorsi saltati: {skipped_by_collision}")

    if not new_entries:
        print("[*] Nessuna nuova estrazione da aggiungere.")
        return

    print(f"[+] Aggiungo {len(new_entries)} nuove estrazioni")

    # Merge + sort cronologico
    merged = existing + new_entries
    merged = sort_history_by_date(merged)

    # Statistiche finali
    ids = [e["concorso"] for e in merged if isinstance(e.get("concorso"), int)]
    if ids:
        print(f"[*] Range concorsi: {min(ids)} - {max(ids)}")
    print(f"[*] Totale: {len(merged)} estrazioni")

    # Distribuzione per anno
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
