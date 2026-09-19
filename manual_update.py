"""
manual_update.py
Aggiorna venus_manual_override.json e (opzionalmente) venus_played.json
con i dati dell'estrazione appena uscita.

- Le sestine giocate vengono registrate sotto il PROSSIMO concorso
  (concorso + 1), perché sono le sestine che verranno giocate per
  l'estrazione successiva a quella appena comunicata.

FIX (2026-09-19):
- #9:  preserve nota esistente in update_played (non più sovrascritta ciecamente)
- #10: validazione formato data DD/MM/YYYY + anno plausibile
- #11: validazione concorso nel range 1-9999
- Import utility condivise da venus_utils
"""
import os
import sys
import re
from datetime import datetime

from venus_utils import load_json, save_json, is_valid_date


OVERRIDE_FILE = "venus_manual_override.json"
PLAYED_FILE = "venus_played.json"

# Range plausibile per il numero concorso
CONCORSO_MIN = 1
CONCORSO_MAX = 9999

# Range plausibile per l'anno
ANNO_MIN = 2020
ANNO_MAX = 2099


# ==========================================
# VALIDAZIONE
# ==========================================
def validate_concorso(value):
    """Ritorna (ok, value, error)."""
    try:
        c = int(value)
    except (ValueError, TypeError):
        return False, 0, f"concorso non valido: '{value}'"
    if not (CONCORSO_MIN <= c <= CONCORSO_MAX):
        return False, c, f"concorso fuori range ({CONCORSO_MIN}-{CONCORSO_MAX}): {c}"
    return True, c, None


def validate_data(value):
    """Ritorna (ok, value, error). Accetta solo DD/MM/YYYY."""
    if not value:
        return False, value, "data mancante"
    s = str(value).strip()
    # Formato DD/MM/YYYY
    if not re.match(r"^\d{2}/\d{2}/\d{4}$", s):
        return False, s, f"data deve essere DD/MM/YYYY: '{s}'"
    # Validazione cronologica + range anno
    if not is_valid_date(s):
        return False, s, f"data non valida cronologicamente: '{s}'"
    anno = int(s[-4:])
    if not (ANNO_MIN <= anno <= ANNO_MAX):
        return False, s, f"anno fuori range ({ANNO_MIN}-{ANNO_MAX}): {anno}"
    return True, s, None


def validate_combinazione(value):
    """Ritorna (ok, list, error). 6 numeri 1-90."""
    nums = parse_combinazione(value)
    if len(nums) != 6:
        return False, nums, f"combinazione deve avere 6 numeri, trovati {len(nums)}"
    if not all(1 <= n <= 90 for n in nums):
        return False, nums, "combinazione contiene numeri fuori range 1-90"
    return True, nums, None


def validate_int_in_range(value, name, lo, hi):
    """Ritorna (ok, int, error)."""
    try:
        v = int(value)
    except (ValueError, TypeError):
        return False, 0, f"{name} non valido: '{value}'"
    if not (lo <= v <= hi):
        return False, v, f"{name} fuori range ({lo}-{hi}): {v}"
    return True, v, None


# ==========================================
# PARSING INPUT
# ==========================================
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
        if len(nums) == 6 and all(1 <= n <= 90 for n in nums):
            result.append(nums)
    return result


# ==========================================
# UPDATE
# ==========================================
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
        "note": f"Concorso {concorso} - aggiornato manualmente",
    }
    save_json(OVERRIDE_FILE, override)


def update_played(concorso, data, sestine):
    """
    Registra le sestine giocate per il concorso indicato.
    Nota: questo concorso è quello PROSSIMO (quello per cui si gioca).

    FIX #9: preserva la nota esistente se presente, invece di sovrascriverla.
    """
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
        # FIX #9: preserva nota esistente se c'era, altrimenti genera
        nota_precedente = existing.get("note", "").strip()
        nuova_nota = f"Concorso {concorso}: {len(sestine)} sestine"

        existing["sestine"] = sestine
        existing["costo_eur"] = float(len(sestine)) * 1.0
        existing["data"] = data
        existing.setdefault("giocata_il", oggi)

        if not nota_precedente or nota_precedente.startswith("Concorso "):
            # Sovrascrivi solo se era vuota o generata automaticamente
            existing["note"] = nuova_nota
        # Altrimenti preserva la nota manuale

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


# ==========================================
# MAIN
# ==========================================
def main():
    print("=== MANUAL UPDATE ===")

    concorso_raw = os.environ.get("MANUAL_CONCORSO", "").strip()
    data_raw = os.environ.get("MANUAL_DATA", "").strip()
    combinazione_raw = os.environ.get("MANUAL_COMBINAZIONE", "").strip()
    jolly_raw = os.environ.get("MANUAL_JOLLY", "").strip()
    superstar_raw = os.environ.get("MANUAL_SUPERSTAR", "").strip()
    jackpot_raw = os.environ.get("MANUAL_JACKPOT", "").strip()
    sestine_raw = os.environ.get("MANUAL_SESTINE", "").strip()

    errors = []

    # FIX #11: validazione concorso
    ok, concorso, err = validate_concorso(concorso_raw)
    if not ok:
        errors.append(err)

    # FIX #10: validazione data
    ok, data, err = validate_data(data_raw)
    if not ok:
        errors.append(err)

    # Validazione combinazione
    ok, combinazione, err = validate_combinazione(combinazione_raw)
    if not ok:
        errors.append(err)

    # Jolly
    ok, jolly, err = validate_int_in_range(jolly_raw, "jolly", 1, 90)
    if not ok:
        errors.append(err)

    # Superstar
    ok, superstar, err = validate_int_in_range(superstar_raw, "superstar", 1, 90)
    if not ok:
        errors.append(err)

    # Jackpot (intero positivo, range ragionevole)
    ok, jackpot, err = validate_int_in_range(
        jackpot_raw, "jackpot", 1_000_000, 500_000_000
    )
    if not ok:
        errors.append(err)

    if errors:
        print("[!] ERRORI DI VALIDAZIONE:")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    print(f"[*] Concorso:     {concorso}")
    print(f"[*] Data:         {data}")
    print(f"[*] Combinazione: {combinazione}")
    print(f"[*] Jolly:        {jolly}")
    print(f"[*] SuperStar:    {superstar}")
    print(f"[*] Jackpot:      EUR {jackpot:,}")

    update_override(concorso, data, combinazione, jolly, superstar, jackpot)

    sestine = parse_sestine(sestine_raw)
    if sestine:
        # Le sestine giocate sono per il PROSSIMO concorso
        next_concorso = concorso + 1
        print(f"[*] Sestine giocate: {len(sestine)}")
        print(f"[*] Registrate per il concorso PROSSIMO: {next_concorso}")
        update_played(next_concorso, data, sestine)
    elif sestine_raw:
        print(f"[!] Sestine giocate: input non valido (attesi 6 numeri 1-90 separati da virgole, "
              f"più sestine separati da |)")
        sys.exit(1)

    print("=== MANUAL UPDATE COMPLETATO ===")


if __name__ == "__main__":
    main()
