"""
generate_update_guide.py
Genera il file UPDATE_HERE.md con istruzioni aggiornate per
compilare venus_manual_override.json con i nuovi numeri.
Eseguito automaticamente dal workflow ad ogni run.
"""
import json
import os
from datetime import datetime

DATABASE_FILE = "venus_database.json"
OUTPUT_FILE = "UPDATE_HERE.md"


def main():
    db = {}
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                db = json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura {DATABASE_FILE}: {e}")

    next_c = db.get("next_contest", {}) or {}
    last_d = db.get("last_draw", {}) or {}

    next_num = next_c.get("number", 0)
    next_date = next_c.get("date", "N/A")
    jackpot = next_c.get("jackpot", 0)

    last_num = last_d.get("contest_number", 0)
    last_date = last_d.get("date", "N/A")
    last_comb = last_d.get("numbers", [0, 0, 0, 0, 0, 0])
    last_jolly = last_d.get("jolly", 0)
    last_superstar = last_d.get("superstar", 0)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    template_json = (
        '{\n'
        f'  "jackpot": {jackpot},\n'
        '  "last_draw": {\n'
        f'    "concorso": {next_num},\n'
        f'    "data": "{next_date}",\n'
        '    "combinazione": [0, 0, 0, 0, 0, 0],\n'
        '    "jolly": 0,\n'
        '    "superstar": 0\n'
        '  },\n'
        f'  "note": "Compila con i numeri reali del concorso {next_num}"\n'
        '}'
    )

    content = f"""# 📝 Aggiorna Venus Vortex — Concorso N° {next_num}

> Ultima generazione automatica: **{now}**

---

## 📊 Stato attuale

| Campo | Valore |
|---|---|
| **Ultima estrazione** | Concorso N° {last_num} del {last_date} |
| **Combinazione** | `{last_comb}` |
| **Jolly** | {last_jolly} |
| **SuperStar** | {last_superstar} |
| **Prossimo concorso** | N° {next_num} del {next_date} |
| **Jackpot attuale** | € {jackpot:,} |

---

## 🎯 Procedura aggiornamento (2 minuti)

### STEP 1 — Trova i numeri veri del concorso {next_num}

Dopo l'estrazione, cerca sul sito ufficiale SuperEnalotto:
- 6 numeri vincenti
- Jolly
- SuperStar

### STEP 2 — Apri il file di override

👉 **LINK DIRETTO:**
