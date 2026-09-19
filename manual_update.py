"""
manual_update.py
Aggiorna venus_manual_override.json e (opzionalmente) venus_played.json
con i dati dell'estrazione appena uscita.

Input via variabili d'ambiente:
- MANUAL_CONCORSO
- MANUAL_DATA
- MANUAL_COMBINAZIONE
- MANUAL_JOLLY
- MANUAL_SUPERSTAR
- MANUAL_JACKPOT
- MANUAL_SESTINE (opzionale)
"""
import json
import os
import sys
from datetime import datetime


OVERRIDE_FILE = "venus_manual_override.json"
PLAYED_FILE = "venus_played.json"


def load_json(filepath, default):
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


def parse_combinazione(s):
    if not s:
        return []
    parts = [x.strip() for x in s.replace(";", ",").split(",") if x.strip()]
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            continue
    return nums


def parse_sestine(s):
    if not s or not s.strip():
        return []
    result = []
    for part in s.split("|"):
        nums = parse_combinazione(part)
        if len(nums) == 6:
            result.append(nums)
    return result


def update_override(concorso, data, combinazione, jolly, superstar, jackpot):
    print(f"[*] Aggiornamento override per concorso {concorso} ({data})")
    override = {
        "jackpot": jackpot,
        "last_draw": {
            "concorso": concorso,
            "data": data,
            "combinazione": combinazione,
            "jolly": jolly,
            "superstar": superstar,
        },
        "note": f"Concorso {concorso} — aggiornato manualmente",
    }
    save_json(OVERRIDE_FILE, override)


def update_played(concorso, data, sestine):
    if not sestine:
        print("[*] Nessuna sestina giocata da registrare.")
        return

    print(f"[*] Registro {len(sestine)} sestine giocate per concorso {concorso}")
    played_data = load_json(PLAYED_FILE, {"played": [], "config": {}})

    if "played" not in played_data:
        played_data["played"] = []
    if "config" not in played_data:
        played_data["config"] = {
            "budget_mensile_eur": 20,
            "budget_annuale_eur": 200,
        }
    if "note" not in played_data:
        played_data["note"] = "Registro delle sestine giocate."

    existing = None
    for play in played_data["played"]:
        if play.get("concorso") == concorso:
            existing = play
            break

    oggi = datetime.now().strftime("%d/%m/%Y")

    if existing:
        existing["sestine"] = sestine
        existing["costo_eur"] = float(len(sestine)) * 1.0
        existing["data"] = data
        existing["giocata_il"] = oggi
        existing["note"] = f"Concorso {concorso}: {len(sestine)} sestine"
        print(f"[+] Concorso {concorso} già presente: aggiornato.")
    else:
        played_data["played"].append({
            "concorso": concorso,
            "data": data,
            "giocata_il": oggi,
            "costo_eur": float(len(sestine)) * 1.0,
            "sestine": sestine,
            "note": f"Concorso {concorso}: {len(sestine)} sestine",
        })
        print(f"[+] Concorso {concorso} aggiunto al registro.")

    save_json(PLAYED_FILE, played_data)


def main():
    print("=== MANUAL UPDATE ===")

    concorso_raw = os.environ.get("MANUAL_CONCORSO", "").strip()
    data = os.environ.get("MANUAL_DATA", "").strip()
    combinazione_raw = os.environ.get("MANUAL_COMBINAZIONE", "").strip()
    jolly_raw = os.environ.get("MANUAL_JOLLY", "").strip()
    superstar_raw = os.environ.get("MANUAL_SUPERSTAR", "").strip()
    jackpot_raw = os.environ.get("MANUAL_JACKPOT", "").strip()
    sestine_raw = os.environ.get("MANUAL_SESTINE", "").strip()

    errors = []

    try:
        concorso = int(concorso_raw)
    except ValueError:
        errors.append(f"concorso non valido: '{concorso_raw}'")
        concorso = 0

    if not data:
        errors.append("data mancante")

    combinazione = parse_combinazione(combinazione_raw)
    if len(combinazione) != 6:
        errors.append(f"combinazione deve avere 6 numeri, trovati {len(combinazione)}")
    if not all(1 <= n <= 90 for n in combinazione):
        errors.append("combinazione contiene numeri fuori range 1-90")

    try:
        jolly = int(jolly_raw)
    except ValueError:
        errors.append(f"jolly non valido: '{jolly_raw}'")
        jolly = 0

    try:
        superstar = int(superstar_raw)
    except ValueError:
        errors.append(f"superstar non valido: '{superstar_raw}'")
        superstar = 0

    try:
        jackpot = int(jackpot_raw)
    except ValueError:
        errors.append(f"jackpot non valido: '{jackpot_raw}'")
        jackpot = 0

    if errors:
        print("[!] ERRORI DI VALIDAZIONE:")
        for e in errors:
            print(f"    • {e}")
        sys.exit(1)

    print(f"[*] Concorso:     {concorso}")
    print(f"[*] Data:         {data}")
    print(f"[*] Combinazione: {combinazione}")
    print(f"[*] Jolly:        {jolly}")
    print(f"[*] SuperStar:    {superstar}")
    print(f"[*] Jackpot:      € {jackpot:,}")

    update_override(concorso, data, combinazione, jolly, superstar, jackpot)

    sestine = parse_sestine(sestine_raw)
    if sestine:
        print(f"[*] Sestine giocate: {len(sestine)}")
        update_played(concorso, data, sestine)

    print("=== MANUAL UPDATE COMPLETATO ===")


if __name__ == "__main__":
    main()
