"""
clean_track_record.py
Rimuove i record orfani dal track record:
- Concorsi con numero > 999 (i 2025 hanno offset +1000, ma se sono "in attesa" sono orfani)
- Concorsi "in attesa" con numero > 999
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


def save_track(data):
    try:
        with open(TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Salvato: {TRACK_FILE}")
    except Exception as e:
        print(f"[!] Errore salvataggio: {e}")


def main():
    print("=== CLEAN TRACK RECORD ===")

    data = load_track()
    records = data.get("records", [])

    print(f"[*] Record attuali: {len(records)}")

    # Filtra: rimuovi record "in attesa" con concorso > 999 (orfani)
    cleaned = []
    removed = []

    for r in records:
        concorso = r.get("target_concorso", 0)
        is_pending = r.get("result") is None

        # Rimuovi solo se: in attesa E concorso > 999 (orfano del 2025)
        if is_pending and isinstance(concorso, int) and concorso > 999:
            removed.append(concorso)
            continue

        cleaned.append(r)

    if not removed:
        print("[*] Nessun record orfano da rimuovere.")
        return

    print(f"[+] Rimuovo {len(removed)} record orfani: {removed}")
    data["records"] = cleaned
    save_track(data)
    print(f"[*] Record finali: {len(cleaned)}")
    print("=== COMPLETATO ===")


if __name__ == "__main__":
    main()
