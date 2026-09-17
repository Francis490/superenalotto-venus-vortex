"""
check_history_gaps.py
Diagnostica: analizza venus_history.json e identifica i concorsi mancanti.
"""
import json
import os

HISTORY_FILE = "venus_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura: {e}")
    return []


def parse_year(date_str):
    """Ritorna l'anno da una data DD/MM/YYYY."""
    try:
        return int(date_str[-4:])
    except Exception:
        return 0


def main():
    print("=== CHECK HISTORY GAPS ===")

    history = load_history()
    print(f"[*] Totale concorsi nel database: {len(history)}")

    # Raggruppa per anno
    by_year = {}
    for item in history:
        y = parse_year(item.get("data", ""))
        if y > 0:
            by_year.setdefault(y, []).append(item)

    # Analizza ogni anno
    for year in sorted(by_year.keys()):
        items = by_year[year]
        ids = sorted(set(item["concorso"] for item in items
                         if isinstance(item.get("concorso"), int)))

        if not ids:
            continue

        min_id = min(ids)
        max_id = max(ids)
        expected = set(range(min_id, max_id + 1))
        actual = set(ids)
        missing = sorted(expected - actual)

        # Duplicati
        all_ids = [item["concorso"] for item in items
                   if isinstance(item.get("concorso"), int)]
        dups = [x for x in set(all_ids) if all_ids.count(x) > 1]

        print(f"\n📅 Anno {year}:")
        print(f"    • Concorsi totali: {len(items)}")
        print(f"    • Range: {min_id} - {max_id}")
        print(f"    • Attesi nel range: {max_id - min_id + 1}")
        print(f"    • Mancanti: {len(missing)}")

        if missing:
            print(f"    • Concorsi mancanti: {missing}")

        if dups:
            print(f"    ⚠️  Duplicati: {dups}")

    # Verifica specifica 2026
    if 2026 in by_year:
        ids_2026 = sorted(set(item["concorso"] for item in by_year[2026]
                              if isinstance(item.get("concorso"), int)))
        if ids_2026:
            expected_2026 = set(range(1, 149))  # 1-148
            actual_2026 = set(ids_2026)
            missing_2026 = sorted(expected_2026 - actual_2026)
            extra_2026 = sorted(actual_2026 - expected_2026)

            print(f"\n🎯 VERIFICA 2026:")
            print(f"    • Attesi: 148 concorsi (1-148)")
            print(f"    • Presenti: {len(actual_2026)}")
            if missing_2026:
                print(f"    • ❌ MANCANTI: {missing_2026}")
            if extra_2026:
                print(f"    • ⚠️  FUORI RANGE: {extra_2026}")

    print("\n=== DIAGNOSTICA COMPLETATA ===")


if __name__ == "__main__":
    main()
