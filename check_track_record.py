"""
check_track_record.py
Diagnostica: mostra il contenuto di venus_track_record.json in formato leggibile.
"""
import json
import os

TRACK_FILE = "venus_track_record.json"


def load_track():
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura: {e}")
    return {"records": []}


def main():
    print("=== CHECK TRACK RECORD ===")

    data = load_track()
    records = data.get("records", [])

    print(f"[*] Record totali: {len(records)}")
    print()

    pending = []
    completed = []

    for r in records:
        concorso = r.get("target_concorso", "N/A")
        mode = r.get("mode", "N/A")
        sestinas = r.get("sestinas", [])
        generated_at = r.get("generated_at", "N/A")[:19]
        result = r.get("result")

        if result is None:
            pending.append((concorso, mode, len(sestinas), generated_at))
        else:
            completed.append((concorso, mode, len(sestinas),
                              result.get("best_hits", 0), generated_at))

    print(f"📊 COMPLETATI ({len(completed)}):")
    if completed:
        for concorso, mode, n_sest, best, gen in completed:
            print(f"    • Concorso {concorso}: {n_sest} sestine · {mode} · "
                  f"best={best} punti · generato {gen}")
    else:
        print("    (nessuno)")

    print()
    print(f"⏳ IN ATTESA ({len(pending)}):")
    if pending:
        for concorso, mode, n_sest, gen in pending:
            print(f"    • Concorso {concorso}: {n_sest} sestine · {mode} · "
                  f"generato {gen}")
    else:
        print("    (nessuno)")

    print()
    print("=== FINE DIAGNOSTICA ===")


if __name__ == "__main__":
    main()
