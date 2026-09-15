"""
build_history_2026.py
Integra i dati REALI 2026 (forniti dall'utente) con lo storico esistente.
Genera i 12 buchi mancanti con seed fisso (sintetici ma riproducibili).

Eseguito dal workflow .github/workflows/generate_history.yml
"""
import json
import os
import random

HISTORY_FILE = "venus_history.json"
RANDOM_SEED = 20260915

# ==========================================
# DATI REALI 2026 (forniti dall'utente)
# Concorsi 1-87 (Gennaio-Maggio 2026)
# ==========================================
REAL_DRAWS = [
    # --- GENNAIO 2026 ---
    {"concorso": 1,  "data": "02/01/2026", "combinazione": [29, 33, 47, 56, 69, 89], "jolly": 16, "superstar": 7},
    {"concorso": 2,  "data": "03/01/2026", "combinazione": [16, 30, 32, 43, 68, 76], "jolly": 36, "superstar": 58},
    {"concorso": 3,  "data": "05/01/2026", "combinazione": [11, 13, 17, 56, 80, 84], "jolly": 41, "superstar": 13},
    {"concorso": 4,  "data": "08/01/2026", "combinazione": [35, 42, 45, 53, 55, 88], "jolly": 66, "superstar": 52},
    {"concorso": 5,  "data": "09/01/2026", "combinazione": [31, 33, 61, 68, 71, 72], "jolly": 87, "superstar": 18},
    {"concorso": 6,  "data": "10/01/2026", "combinazione": [11, 19, 24, 66, 82, 88], "jolly": 58, "superstar": 48},
    {"concorso": 7,  "data": "12/01/2026", "combinazione": [1, 11, 40, 73, 75, 81],  "jolly": 70, "superstar": 22},
    {"concorso": 8,  "data": "13/01/2026", "combinazione": [20, 29, 56, 68, 72, 74], "jolly": 35, "superstar": 50},
    {"concorso": 9,  "data": "15/01/2026", "combinazione": [44, 49, 60, 69, 73, 85], "jolly": 36, "superstar": 1},
    {"concorso": 10, "data": "16/01/2026", "combinazione": [14, 21, 24, 52, 80, 86], "jolly": 57, "superstar": 14},
    {"concorso": 11, "data": "17/01/2026", "combinazione": [3, 7, 41, 56, 65, 83],   "jolly": 79, "superstar": 82},
    {"concorso": 12, "data": "20/01/2026", "combinazione": [8, 13, 25, 60, 72, 74],  "jolly": 78, "superstar": 34},
    {"concorso": 13, "data": "22/01/2026", "combinazione": [2, 30, 52, 56, 57, 78],  "jolly": 59, "superstar": 25},
    {"concorso": 14, "data": "23/01/2026", "combinazione": [2, 6, 11, 19, 88, 90],   "jolly": 69, "superstar": 52},
    {"concorso": 15, "data": "24/01/2026", "combinazione": [22, 37, 55, 61, 68, 71], "jolly": 21, "superstar": 18},
    # 16-19 MANCANTI (verranno generati)
    # --- FEBBRAIO 2026 ---
    {"concorso": 20, "data": "03/02/2026", "combinazione": [11, 16, 17, 41, 42, 46], "jolly": 70, "superstar": 57},
    {"concorso": 21, "data": "05/02/2026", "combinazione": [6, 8, 26, 27, 57, 90],   "jolly": 41, "superstar": 30},
    {"concorso": 22, "data": "06/02/2026", "combinazione": [6, 8, 17, 31, 36, 75],   "jolly": 90, "superstar": 82},
    {"concorso": 23, "data": "07/02/2026", "combinazione": [4, 7, 12, 30, 69, 81],   "jolly": 41, "superstar": 67},
    {"concorso": 24, "data": "10/02/2026", "combinazione": [1, 15, 29, 39, 63, 83],  "jolly": 73, "superstar": 21},
    {"concorso": 25, "data": "12/02/2026", "combinazione": [5, 11, 35, 52, 80, 85],  "jolly": 66, "superstar": 29},
    {"concorso": 26, "data": "13/02/2026", "combinazione": [1, 52, 57, 71, 76, 83],  "jolly": 37, "superstar": 3},
    {"concorso": 27, "data": "14/02/2026", "combinazione": [5, 23, 40, 47, 80, 85],  "jolly": 6, "superstar": 47},
    {"concorso": 28, "data": "17/02/2026", "combinazione": [16, 21, 42, 45, 52, 88], "jolly": 58, "superstar": 21},
    {"concorso": 29, "data": "19/02/2026", "combinazione": [20, 39, 40, 43, 76, 90], "jolly": 53, "superstar": 53},
    {"concorso": 30, "data": "20/02/2026", "combinazione": [30, 34, 41, 42, 49, 83], "jolly": 64, "superstar": 77},
    {"concorso": 31, "data": "21/02/2026", "combinazione": [49, 58, 60, 66, 68, 81], "jolly": 75, "superstar": 58},
    {"concorso": 32, "data": "24/02/2026", "combinazione": [4, 18, 23, 26, 45, 87],  "jolly": 82, "superstar": 29},
    {"concorso": 33, "data": "26/02/2026", "combinazione": [18, 30, 36, 52, 67, 72], "jolly": 69, "superstar": 47},
    {"concorso": 34, "data": "27/02/2026", "combinazione": [10, 14, 49, 55, 71, 79], "jolly": 80, "superstar": 36},
    # 35 MANCANTE (verrà generato)
    # --- MARZO 2026 ---
    {"concorso": 36, "data": "03/03/2026", "combinazione": [4, 16, 42, 48, 56, 68],  "jolly": 26, "superstar": 83},
    {"concorso": 37, "data": "05/03/2026", "combinazione": [7, 23, 39, 62, 63, 78],  "jolly": 22, "superstar": 35},
    {"concorso": 38, "data": "06/03/2026", "combinazione": [4, 17, 22, 37, 50, 88],  "jolly": 20, "superstar": 2},
    {"concorso": 39, "data": "07/03/2026", "combinazione": [3, 12, 18, 40, 45, 69],  "jolly": 5, "superstar": 49},
    {"concorso": 40, "data": "10/03/2026", "combinazione": [8, 34, 42, 47, 55, 83],  "jolly": 4, "superstar": 42},
    {"concorso": 41, "data": "12/03/2026", "combinazione": [8, 24, 25, 62, 63, 64],  "jolly": 43, "superstar": 54},
    {"concorso": 42, "data": "13/03/2026", "combinazione": [3, 11, 13, 20, 53, 61],  "jolly": 88, "superstar": 43},
    {"concorso": 43, "data": "14/03/2026", "combinazione": [3, 6, 33, 63, 88, 89],   "jolly": 18, "superstar": 87},
    {"concorso": 44, "data": "17/03/2026", "combinazione": [2, 13, 16, 41, 53, 56],  "jolly": 60, "superstar": 6},
    {"concorso": 45, "data": "19/03/2026", "combinazione": [19, 39, 45, 54, 62, 89], "jolly": 42, "superstar": 45},
    {"concorso": 46, "data": "20/03/2026", "combinazione": [14, 32, 45, 51, 54, 87], "jolly": 61, "superstar": 50},
    {"concorso": 47, "data": "21/03/2026", "combinazione": [9, 26, 33, 49, 51, 55],  "jolly": 50, "superstar": 4},
    {"concorso": 48, "data": "24/03/2026", "combinazione": [6, 54, 60, 64, 74, 87],  "jolly": 10, "superstar": 65},
    {"concorso": 49, "data": "26/03/2026", "combinazione": [24, 26, 39, 69, 77, 80], "jolly": 82, "superstar": 3},
    {"concorso": 50, "data": "27/03/2026", "combinazione": [6, 22, 27, 43, 58, 64],  "jolly": 10, "superstar": 74},
    # 51-52 MANCANTI (verranno generati)
    # --- APRILE 2026 ---
    {"concorso": 53, "data": "02/04/2026", "combinazione": [18, 24, 25, 32, 36, 63], "jolly": 40, "superstar": 80},
    {"concorso": 54, "data": "03/04/2026", "combinazione": [28, 52, 53, 64, 66, 72], "jolly": 44, "superstar": 6},
    {"concorso": 55, "data": "04/04/2026", "combinazione": [8, 21, 29, 46, 60, 81],  "jolly": 42, "superstar": 80},
    {"concorso": 56, "data": "07/04/2026", "combinazione": [10, 16, 18, 47, 50, 59], "jolly": 7, "superstar": 60},
    {"concorso": 57, "data": "09/04/2026", "combinazione": [2, 30, 38, 63, 74, 84],  "jolly": 19, "superstar": 82},
    {"concorso": 58, "data": "10/04/2026", "combinazione": [3, 10, 13, 17, 58, 90],  "jolly": 32, "superstar": 7},
    {"concorso": 59, "data": "11/04/2026", "combinazione": [19, 28, 38, 48, 77, 85], "jolly": 59, "superstar": 57},
    {"concorso": 60, "data": "14/04/2026", "combinazione": [3, 5, 20, 27, 35, 66],   "jolly": 17, "superstar": 6},
    {"concorso": 61, "data": "16/04/2026", "combinazione": [9, 11, 12, 38, 44, 54],  "jolly": 60, "superstar": 39},
    {"concorso": 62, "data": "17/04/2026", "combinazione": [13, 27, 45, 53, 57, 84], "jolly": 34, "superstar": 63},
    {"concorso": 63, "data": "18/04/2026", "combinazione": [11, 22, 28, 33, 68, 77], "jolly": 9, "superstar": 70},
    {"concorso": 64, "data": "21/04/2026", "combinazione": [18, 19, 40, 43, 56, 77], "jolly": 6, "superstar": 65},
    {"concorso": 65, "data": "23/04/2026", "combinazione": [18, 24, 28, 35, 56, 58], "jolly": 72, "superstar": 57},
    {"concorso": 66, "data": "24/04/2026", "combinazione": [6, 13, 33, 37, 68, 82],  "jolly": 56, "superstar": 20},
    {"concorso": 67, "data": "27/04/2026", "combinazione": [40, 57, 62, 64, 85, 87], "jolly": 23, "superstar": 56},
    # 68-69 MANCANTI (verranno generati)
    # --- MAGGIO 2026 ---
    {"concorso": 70, "data": "02/05/2026", "combinazione": [7, 58, 60, 79, 84, 86],  "jolly": 2, "superstar": 19},
    {"concorso": 71, "data": "04/05/2026", "combinazione": [3, 14, 31, 46, 61, 63],  "jolly": 75, "superstar": 24},
    {"concorso": 72, "data": "05/05/2026", "combinazione": [24, 34, 45, 55, 81, 87], "jolly": 23, "superstar": 52},
    {"concorso": 73, "data": "07/05/2026", "combinazione": [1, 34, 48, 66, 69, 73],  "jolly": 75, "superstar": 58},
    {"concorso": 74, "data": "08/05/2026", "combinazione": [8, 16, 41, 47, 51, 90],  "jolly": 82, "superstar": 69},
    {"concorso": 75, "data": "09/05/2026", "combinazione": [9, 27, 30, 42, 43, 62],  "jolly": 11, "superstar": 11},
    {"concorso": 76, "data": "12/05/2026", "combinazione": [2, 28, 31, 57, 58, 59],  "jolly": 5, "superstar": 2},
    {"concorso": 77, "data": "14/05/2026", "combinazione": [31, 56, 72, 74, 84, 85], "jolly": 18, "superstar": 34},
    {"concorso": 78, "data": "15/05/2026", "combinazione": [5, 13, 17, 28, 47, 68],  "jolly": 42, "superstar": 19},
    {"concorso": 79, "data": "16/05/2026", "combinazione": [7, 12, 60, 69, 89, 90],  "jolly": 59, "superstar": 36},
    {"concorso": 80, "data": "19/05/2026", "combinazione": [49, 57, 61, 73, 79, 86], "jolly": 8, "superstar": 36},
    {"concorso": 81, "data": "21/05/2026", "combinazione": [1, 38, 57, 58, 64, 81],  "jolly": 28, "superstar": 50},
    {"concorso": 82, "data": "22/05/2026", "combinazione": [5, 17, 65, 71, 83, 87],  "jolly": 50, "superstar": 86},
    {"concorso": 83, "data": "23/05/2026", "combinazione": [14, 29, 34, 57, 59, 69], "jolly": 20, "superstar": 16},
    {"concorso": 84, "data": "26/05/2026", "combinazione": [7, 10, 35, 41, 45, 61],  "jolly": 2, "superstar": 45},
    # 85-87 MANCANTI (verranno generati)
]

# Concorsi mancanti da generare (con date stimate)
MISSING_DRAWS = [
    {"concorso": 16, "data": "27/01/2026"},
    {"concorso": 17, "data": "29/01/2026"},
    {"concorso": 18, "data": "30/01/2026"},
    {"concorso": 19, "data": "31/01/2026"},
    {"concorso": 35, "data": "28/02/2026"},
    {"concorso": 51, "data": "28/03/2026"},
    {"concorso": 52, "data": "31/03/2026"},
    {"concorso": 68, "data": "28/04/2026"},
    {"concorso": 69, "data": "30/04/2026"},
    {"concorso": 85, "data": "28/05/2026"},
    {"concorso": 86, "data": "29/05/2026"},
    {"concorso": 87, "data": "30/05/2026"},
]


def generate_synthetic_draw(concorso, data, rng):
    """Genera un'estrazione sintetica ma realistica."""
    sestina = sorted(rng.sample(range(1, 91), 6))
    available = [n for n in range(1, 91) if n not in sestina]
    jolly = rng.choice(available)
    remaining = [n for n in available if n != jolly]
    superstar = rng.choice(remaining)
    return {
        "concorso": concorso,
        "data": data,
        "combinazione": sestina,
        "jolly": jolly,
        "superstar": superstar,
    }


def main():
    print("=== BUILD HISTORY 2026 (REAL + SYNTHETIC) ===")

    # 1) Leggi storico esistente (per i concorsi 88+)
    existing = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura: {e}")

    # Rimuovi dal file esistente i concorsi < 88 (verranno sostituiti con dati reali)
    filtered_existing = [item for item in existing
                         if isinstance(item.get("concorso"), int)
                         and item["concorso"] >= 88]
    print(f"[*] Concorsi >= 88 già presenti: {len(filtered_existing)}")

    # 2) Genera i buchi con seed fisso
    rng = random.Random(RANDOM_SEED)
    synthetic_draws = [
        generate_synthetic_draw(m["concorso"], m["data"], rng)
        for m in MISSING_DRAWS
    ]
    print(f"[+] Generati {len(synthetic_draws)} concorsi sintetici (buchi)")

    # 3) Unisci tutto
    merged = REAL_DRAWS + synthetic_draws + filtered_existing
    merged.sort(key=lambda x: x.get("concorso", 0))
    print(f"[+] Totale finale: {len(merged)} concorsi")

    # 4) Salva
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)
    print(f"[+] File salvato: {HISTORY_FILE}")

    # Report finale
    ids = [item["concorso"] for item in merged]
    print(f"[*] Range: {min(ids)} -> {max(ids)}")
    print("=== COMPLETATO ===")


if __name__ == "__main__":
    main()
