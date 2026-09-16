"""
generate_update_guide.py
Genera il file UPDATE_HERE.md con istruzioni aggiornate per
compilare venus_manual_override.json con i nuovi numeri.
Eseguito automaticamente dal workflow ad ogni run.

Versione robusta: costruzione del contenuto via lista di righe,
nessun uso di triple-quote per evitare problemi di parsing.
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
            print("[!] Errore lettura " + DATABASE_FILE + ": " + str(e))

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

    # --- JSON template come stringa (costruito per concatenazione) ---
    json_template_lines = [
        "{",
        '  "jackpot": ' + str(jackpot) + ",",
        '  "last_draw": {',
        '    "concorso": ' + str(next_num) + ",",
        '    "data": "' + str(next_date) + '",',
        '    "combinazione": [0, 0, 0, 0, 0, 0],',
        '    "jolly": 0,',
        '    "superstar": 0',
        '  },',
        '  "note": "Compila con i numeri reali del concorso ' + str(next_num) + '"',
        "}",
    ]
    json_template = "\n".join(json_template_lines)

    # --- Contenuto markdown costruito per righe ---
    lines = []

    lines.append("# Aggiorna Venus Vortex - Concorso N. " + str(next_num))
    lines.append("")
    lines.append("> Ultima generazione automatica: **" + now + "**")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Stato attuale")
    lines.append("")
    lines.append("| Campo | Valore |")
    lines.append("|---|---|")
    lines.append("| **Ultima estrazione** | Concorso N. " + str(last_num) + " del " + str(last_date) + " |")
    lines.append("| **Combinazione** | `" + str(last_comb) + "` |")
    lines.append("| **Jolly** | " + str(last_jolly) + " |")
    lines.append("| **SuperStar** | " + str(last_superstar) + " |")
    lines.append("| **Prossimo concorso** | N. " + str(next_num) + " del " + str(next_date) + " |")
    lines.append("| **Jackpot attuale** | EUR " + format(jackpot, ",") + " |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Procedura aggiornamento (2 minuti)")
    lines.append("")
    lines.append("### STEP 1 - Trova i numeri veri del concorso " + str(next_num))
    lines.append("")
    lines.append("Dopo l'estrazione, cerca sul sito ufficiale SuperEnalotto:")
    lines.append("- 6 numeri vincenti")
    lines.append("- Jolly")
    lines.append("- SuperStar")
    lines.append("")
    lines.append("### STEP 2 - Apri il file di override")
    lines.append("")
    lines.append("Link diretto:")
    lines.append("")
    lines.append("```")
    lines.append("https://github.com/Francis490/superenalotto-venus-vortex/edit/main/venus_manual_override.json")
    lines.append("```")
    lines.append("")
    lines.append("### STEP 3 - Sostituisci il contenuto con questo template")
    lines.append("")
    lines.append("```json")
    lines.append(json_template)
    lines.append("```")
    lines.append("")
    lines.append("**Sostituisci:**")
    lines.append("- `[0, 0, 0, 0, 0, 0]` con i 6 numeri veri (ordine crescente)")
    lines.append("- `\"jolly\": 0` con il Jolly vero")
    lines.append("- `\"superstar\": 0` con il SuperStar vero")
    lines.append("- `\"jackpot\": " + str(jackpot) + "` con il nuovo jackpot (o lascia invariato)")
    lines.append("")
    lines.append("### STEP 4 - Commit changes")
    lines.append("")
    lines.append("In fondo alla pagina, clicca **Commit changes**.")
    lines.append("")
    lines.append("### STEP 5 - Lancia il workflow")
    lines.append("")
    lines.append("Link diretto:")
    lines.append("")
    lines.append("```")
    lines.append("https://github.com/Francis490/superenalotto-venus-vortex/actions/workflows/venus_sync.yml")
    lines.append("```")
    lines.append("")
    lines.append("Clicca **Run workflow** -> **main** -> **Run**.")
    lines.append("")
    lines.append("### STEP 6 - Fatto!")
    lines.append("")
    lines.append("Dopo ~60 secondi ricevi il report Telegram con i nuovi dati.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Orari estrazioni SuperEnalotto")
    lines.append("")
    lines.append("| Giorno | Ora |")
    lines.append("|---|---|")
    lines.append("| Martedi | 20:00 |")
    lines.append("| Giovedi | 20:00 |")
    lines.append("| Venerdi | 20:00 |")
    lines.append("| Sabato | 20:00 |")
    lines.append("")
    lines.append("Aggiorna il file **dopo le 20:30**.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generato automaticamente da Venus Vortex - Cosmic Pattern Engine*")
    lines.append("")

    content = "\n".join(lines)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("[+] Generato: " + OUTPUT_FILE)
    print("[*] Concorso di riferimento: " + str(next_num) + " del " + str(next_date))


if __name__ == "__main__":
    main()
