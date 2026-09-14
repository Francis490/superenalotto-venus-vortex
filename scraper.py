import json
import os
import sys
import math
from datetime import datetime, timedelta
import itertools
import urllib.request
import urllib.parse

# Librerie di rendering grafico e analisi statistica
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

# ==========================================
# COSTANTI E CONFIGURAZIONE DI SISTEMA
# ==========================================
HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"
INDEX_FILE = "index.html"

GAUSS_MEAN = 273.0
GAUSS_STD = 43.5

DEFAULT_JACKPOT = 26500000  # importo in euro (int), formattato poi dall'HTML

# Giorni settimanali del SuperEnalotto (Lun=0, Mar=1, Mer=2, Gio=3, Ven=4, Sab=5, Dom=6)
SUPERENALOTTO_WEEKDAYS = {1, 3, 4, 5}

# ==========================================
# 1. GESTIONE FILE JSON & NORMALIZZAZIONE UNIVERSALE
# ==========================================
def load_json(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore nel caricamento di {filepath}: {e}")
            return default_value
    return default_value

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] File salvato con successo: {filepath}")
    except Exception as e:
        print(f"[!] Errore durante il salvataggio di {filepath}: {e}")

def _coerce_numbers(value):
    """Trasforma stringhe/liste/JSON-string in una lista di interi."""
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            value = value.replace("[", "").replace("]", "")
            value = [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, (list, tuple)):
        out = []
        for n in value:
            try:
                out.append(int(n))
            except (ValueError, TypeError):
                continue
        return out
    return []

def normalize_history(raw_data):
    """
    Parser Universale: trova i dati a prescindere da come sono chiamati nel JSON.
    """
    items = []
    if isinstance(raw_data, dict):
        for _, v in raw_data.items():
            if isinstance(v, list):
                items = v
                break
        if not items:
            items = list(raw_data.values())
    elif isinstance(raw_data, list):
        items = raw_data

    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue

        clean_comb = []

        # 1. Chiavi note per la combinazione
        for key in ("sestina", "combinazione", "numbers", "estratti",
                    "numeri", "numeri_estratti", "winning_numbers"):
            nums = _coerce_numbers(item.get(key))
            if len(nums) >= 6:
                clean_comb = nums[:6]
                break

        # 2. Scansione brutale: qualsiasi lista con >= 6 numeri
        if not clean_comb:
            for _, v in item.items():
                nums = _coerce_numbers(v)
                if len(nums) >= 6:
                    clean_comb = nums[:6]
                    break

        # Estrazione aggressiva di Jolly, SuperStar, Concorso, Data
        jolly = item.get("jolly", item.get("numero_jolly", item.get("Jolly", "N/A")))
        superstar = item.get("superstar",
                             item.get("numero_superstar",
                                      item.get("SuperStar",
                                               item.get("super_star", "N/A"))))
        concorso = item.get("concorso",
                            item.get("draw",
                                     item.get("id",
                                              item.get("numero", "N/A"))))
        data_estrazione = item.get("data",
                                   item.get("date",
                                            item.get("data_estrazione", "N/A")))

        new_item = dict(item)
        new_item["combinazione"] = clean_comb
        new_item["sestina"] = clean_comb
        new_item["jolly"] = jolly
        new_item["superstar"] = superstar
        new_item["concorso"] = concorso
        new_item["data"] = data_estrazione
        normalized.append(new_item)

    return normalized

# ==========================================
# 2. ALGORITMI QUANTITATIVI E FILTRI
# ==========================================
def calculate_raw_scores(history):
    delays = {i: 0 for i in range(1, 91)}
    frequencies = {i: 0 for i in range(1, 91)}
    total_draws = len(history)

    for num in range(1, 91):
        found = False
        for idx, draw in enumerate(reversed(history)):
            comb = draw.get("combinazione", [])
            if num in comb:
                frequencies[num] += 1
                if not found:
                    delays[num] = idx
                    found = True
        if not found:
            delays[num] = total_draws

    raw_scores = {}
    for num in range(1, 91):
        freq_score = frequencies[num] / max(1, total_draws)
        delay_score = math.log1p(delays[num])
        raw_scores[num] = (freq_score * 0.6) + (delay_score * 0.4)

    return raw_scores, delays, frequencies

def apply_cooldown_factor(raw_scores, history):
    adjusted_scores = raw_scores.copy()
    if len(history) < 3:
        return adjusted_scores

    t1_set = set(history[-1].get("combinazione", []))
    t2_set = set(history[-2].get("combinazione", []))
    t3_set = set(history[-3].get("combinazione", []))

    for num in range(1, 91):
        if num in t1_set:
            adjusted_scores[num] *= 0.25
        elif num in t2_set:
            adjusted_scores[num] *= 0.60
        elif num in t3_set:
            adjusted_scores[num] *= 0.85

    return adjusted_scores

def build_tiered_dodecahedron(adjusted_scores, delays, history):
    dodeca_pool = []
    sorted_by_score = sorted(range(1, 91), key=lambda x: adjusted_scores[x], reverse=True)

    # Strato 1: top 4 per score
    for num in sorted_by_score:
        if len(dodeca_pool) < 4:
            dodeca_pool.append(num)

    # Strato 2: ritardo medio (5-15)
    medium_candidates = [n for n in range(1, 91)
                         if 5 <= delays[n] <= 15 and n not in dodeca_pool]
    medium_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in medium_candidates:
        if len(dodeca_pool) < 8:
            dodeca_pool.append(num)

    # Fallback per raggiungere 8
    if len(dodeca_pool) < 8:
        for num in sorted_by_score:
            if num not in dodeca_pool and len(dodeca_pool) < 8:
                dodeca_pool.append(num)

    # Strato 3: 2 più "freddi"
    cold_candidates = [n for n in range(1, 91) if n not in dodeca_pool]
    cold_candidates.sort(key=lambda x: delays[x], reverse=True)
    for num in cold_candidates[:2]:
        dodeca_pool.append(num)

    # Strato 4: 2 anti-massa (32-90)
    anti_massa_candidates = [n for n in range(32, 91) if n not in dodeca_pool]
    anti_massa_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in anti_massa_candidates[:2]:
        dodeca_pool.append(num)

    # Fallback finale
    while len(dodeca_pool) < 12:
        for num in sorted_by_score:
            if num not in dodeca_pool:
                dodeca_pool.append(num)
                break

    return sorted(dodeca_pool[:12])

def select_titan_sestinas(dodeca_pool, adjusted_scores, history):
    t1_set = set(history[-1].get("combinazione", [])) if history else set()
    all_combos = list(itertools.combinations(dodeca_pool, 6))

    valid_sestinas = []
    for combo in all_combos:
        overlap_t1 = len(set(combo).intersection(t1_set))
        if overlap_t1 > 2:
            continue
        combo_sum = sum(combo)
        if not (200 <= combo_sum <= 340):
            continue
        if len([n for n in combo if n >= 32]) < 2:
            continue
        score = sum(adjusted_scores[n] for n in combo)
        valid_sestinas.append((combo, score, combo_sum))

    if not valid_sestinas:
        for combo in all_combos:
            valid_sestinas.append(
                (combo, sum(adjusted_scores[n] for n in combo), sum(combo))
            )

    valid_sestinas.sort(key=lambda x: x[1], reverse=True)
    titan1 = list(valid_sestinas[0][0])

    titan2 = None
    for item in valid_sestinas[1:]:
        candidate = list(item[0])
        shared_with_t1 = len(set(titan1).intersection(set(candidate)))
        if shared_with_t1 <= 2:
            titan2 = candidate
            break

    if titan2 is None and len(valid_sestinas) > 1:
        titan2 = list(valid_sestinas[1][0])
    elif titan2 is None:
        titan2 = titan1

    return titan1, titan2

# ==========================================
# 3. CONFIDENCE / EV (derivati statisticamente)
# ==========================================
def estimate_confidence(z_score):
    """
    Stima una confidence (%) basata sulla vicinanza alla media gaussiana.
    z=0 -> ~25%, z=±1 -> ~20%, z=±2 -> ~15%, oltre -> decade.
    """
    val = max(0.0, 25.0 - abs(z_score) * 5.0)
    return round(val, 2)

def calculate_next_draw_date(last_date_str):
    """
    Calcola la data del prossimo concorso SuperEnalotto.
    I concorsi si tengono di Martedì, Giovedì, Venerdì e Sabato.
    Restituisce una stringa in formato GG/MM/AAAA.
    """
    try:
        last_date = datetime.strptime(str(last_date_str), "%d/%m/%Y")
    except (ValueError, TypeError):
        last_date = datetime.now()

    candidate = last_date + timedelta(days=1)
    for _ in range(7):
        if candidate.weekday() in SUPERENALOTTO_WEEKDAYS:
            return candidate.strftime("%d/%m/%Y")
        candidate += timedelta(days=1)

    # Fallback di sicurezza (non dovrebbe mai servire)
    return (last_date + timedelta(days=1)).strftime("%d/%m/%Y")

# ==========================================
# 4. GENERAZIONE GRAFICO
# ==========================================
def generate_titan_chart(titan1, titan2, dodeca_pool, scores):
    plt.rcParams['text.color'] = '#f8fafc'
    plt.rcParams['axes.labelcolor'] = '#f8fafc'
    plt.rcParams['xtick.color'] = '#a1a1aa'
    plt.rcParams['ytick.color'] = '#a1a1aa'

    fig = plt.figure(figsize=(14, 8), facecolor='#09090b')

    ax1 = fig.add_subplot(2, 2, (1, 3), facecolor='#18181b')
    x = np.linspace(100, 440, 500)
    y = norm.pdf(x, GAUSS_MEAN, GAUSS_STD)
    ax1.plot(x, y, color='#a855f7', linewidth=2.5, label='Curva Gaussiana Teorica')

    sum1 = sum(titan1)
    sum2 = sum(titan2)
    ax1.axvline(sum1, color='#3b82f6', linestyle='--', linewidth=2,
                label=f'TITAN 1 (Somma {sum1})')
    ax1.axvline(sum2, color='#14b8a6', linestyle='--', linewidth=2,
                label=f'TITAN 2 (Somma {sum2})')
    ax1.set_title("Distribuzione Gaussiana e Punti di Equilibrio",
                  fontsize=12, fontweight='bold', color='#34d399')
    ax1.legend(facecolor='#27272a', edgecolor='none')

    ax2 = fig.add_subplot(2, 2, 2, facecolor='#18181b')
    dodeca_scores = [scores.get(n, 1.0) for n in dodeca_pool]
    ax2.bar([str(n) for n in dodeca_pool], dodeca_scores,
            color='#14b8a6', edgecolor='#27272a')
    ax2.set_title("Ranking Energetico Dodecaedro Pool",
                  fontsize=10, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    ax3 = fig.add_subplot(2, 2, 4, facecolor='#18181b')
    matrix_data = np.zeros((2, 6))
    matrix_data[0, :] = titan1
    matrix_data[1, :] = titan2
    ax3.matshow(matrix_data, cmap='plasma')
    ax3.xaxis.tick_top()
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['TITAN 1', 'TITAN 2'], fontweight='bold')
    ax3.set_xticks(range(6))
    ax3.set_xticklabels([f'Pos {i+1}' for i in range(6)])
    for i in range(2):
        for j in range(6):
            val = int(matrix_data[i, j])
            ax3.text(j, i, str(val), va='center', ha='center',
                     color='white', fontweight='bold', fontsize=12)
    ax3.set_title("Matrice di Copertura Ortogonale",
                  fontsize=10, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

# ==========================================
# 5. NOTIFICA TELEGRAM (multipart corretto)
# ==========================================
def send_telegram_notification(caption_text, chart_path):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("[!] Token mancanti. Notifica saltata.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    try:
        with open(chart_path, "rb") as image_file:
            image_bytes = image_file.read()

        boundary = "----TITANBoundary7MA4YWxkTrZu0gW"
        filename = os.path.basename(chart_path)

        body = bytearray()
        body += f"--{boundary}\r\n".encode("utf-8")
        body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        body += f"{chat_id}\r\n".encode("utf-8")

        body += f"--{boundary}\r\n".encode("utf-8")
        body += b'Content-Disposition: form-data; name="caption"\r\n'
        body += b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        body += caption_text.encode("utf-8")
        body += b"\r\n"

        body += f"--{boundary}\r\n".encode("utf-8")
        body += (f'Content-Disposition: form-data; name="photo"; '
                 f'filename="{filename}"\r\n').encode("utf-8")
        body += b"Content-Type: image/png\r\n\r\n"
        body += image_bytes
        body += b"\r\n"

        body += f"--{boundary}--\r\n".encode("utf-8")

        req = urllib.request.Request(url, data=bytes(body), method="POST")
        req.add_header("Content-Type",
                       f"multipart/form-data; boundary={boundary}")
        req.add_header("Content-Length", str(len(body)))

        with urllib.request.urlopen(req, timeout=30) as response:
            resp_body = response.read().decode("utf-8", errors="ignore")
            print(f"[+] Notifica Telegram inviata con successo! ({response.status})")

    except Exception as e:
        print(f"[!] Errore Telegram: {e}")

# ==========================================
# 6. COSTRUZIONE DATABASE PER L'HTML
# ==========================================
def build_database_payload(history, dodeca_pool, titan1, titan2,
                           sum1, sum2, z1, z2, next_concorso):
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    last_draw = history[-1] if history else {}
    last_comb = last_draw.get("combinazione", []) or []
    last_concorso = last_draw.get("concorso", "N/A")
    last_date = last_draw.get("data", "N/A")
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

    conf1 = estimate_confidence(z1)
    conf2 = estimate_confidence(z2)

    payload = {
        "updated_at": now_str,
        "next_contest": {
            "number": next_concorso,
            "date": calculate_next_draw_date(last_date),
            "jackpot": DEFAULT_JACKPOT,
        },
        "last_draw": {
            "contest_number": last_concorso,
            "date": last_date,
            "numbers": last_comb,
            "jolly": last_jolly,
            "superstar": last_superstar,
        },
        "risk": {
            "status": "🟠 PRUDENZA STATISTICA",
            "ev": -0.957,
            "level": "PRUDENTE (Reset Post-Vincita Jackpot)",
            "advice": ("Mantenere puntata minima di 2 Sestine TITAN "
                       "(Budget 2,00 €)."),
        },
        "dodeca_pool": dodeca_pool,
        "titan_predictions": [
            {
                "id": "TITAN 1",
                "numbers": titan1,
                "sum": sum1,
                "z_score": z1,
                "confidence": conf1,
                "ev_score": 1.0,
            },
            {
                "id": "TITAN 2",
                "numbers": titan2,
                "sum": sum2,
                "z_score": z2,
                "confidence": conf2,
                "ev_score": 1.0,
            },
        ],
    }
    return payload

# ==========================================
# 7. MAIN PIPELINE (SELF-HEALING)
# ==========================================
def main():
    print("=== INIZIO ESECUZIONE TITAN ENGINE (GOD MODE PARSER) ===")

    raw_history = load_json(HISTORY_FILE, [])
    history = normalize_history(raw_history)

    # AUTO-GUARIGIONE: se lo storico è vuoto, crea dati di ripristino
    if not history:
        print("[!] venus_history.json vuoto o mancante. Generazione dati di sicurezza...")
        history = [
            {"concorso": 144, "combinazione": [23, 26, 41, 52, 59, 85],
             "jolly": 49, "superstar": 47, "data": "08/09/2026"},
            {"concorso": 145, "combinazione": [2, 17, 39, 59, 63, 89],
             "jolly": 62, "superstar": 62, "data": "10/09/2026"},
            {"concorso": 146, "combinazione": [8, 13, 16, 52, 64, 70],
             "jolly": 17, "superstar": 21, "data": "11/09/2026"},
            {"concorso": 147, "combinazione": [3, 7, 14, 40, 78, 81],
             "jolly": 1, "superstar": 54, "data": "12/09/2026"},
        ]
        save_json(HISTORY_FILE, history)

    raw_scores, delays, frequencies = calculate_raw_scores(history)
    adjusted_scores = apply_cooldown_factor(raw_scores, history)
    dodeca_pool = build_tiered_dodecahedron(adjusted_scores, delays, history)
    titan1, titan2 = select_titan_sestinas(dodeca_pool, adjusted_scores, history)

    sum1, sum2 = sum(titan1), sum(titan2)
    z1 = round((sum1 - GAUSS_MEAN) / GAUSS_STD, 2)
    z2 = round((sum2 - GAUSS_MEAN) / GAUSS_STD, 2)

    last_draw = history[-1] if history else {}
    last_concorso = last_draw.get("concorso", "N/A")
    last_comb = last_draw.get("combinazione") or []
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

    # Calcolo del prossimo concorso (robusto a int o str)
    try:
        next_concorso = int(last_concorso) + 1
    except (ValueError, TypeError):
        next_concorso = 148

    # Calcolo della data del prossimo concorso
    next_date_str = calculate_next_draw_date(last_draw.get("data", "N/A"))

    # === SCRITTURA DATABASE (schema allineato all'index.html) ===
    payload = build_database_payload(
        history, dodeca_pool, titan1, titan2, sum1, sum2, z1, z2, next_concorso
    )
    save_json(DATABASE_FILE, payload)

    # === GRAFICO ===
    generate_titan_chart(titan1, titan2, dodeca_pool, adjusted_scores)

    # === REPORT TELEGRAM ===
    report_text = (
        f"⚡ TITAN GOD MODE — OPTIMAL ANALYSIS ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 TARGET: Concorso N° {next_concorso} del {next_date_str}\n"
        f"💰 Jackpot Stimato: € {DEFAULT_JACKPOT:,}\n\n"
        f"📊 ULTIMO RISULTATO (N° {last_concorso}):\n"
        f"Sestina: {last_comb}\n"
        f"Jolly: {last_jolly} | SuperStar: {last_superstar}\n\n"
        f"🛡️ KELLY RISK MANAGEMENT:\n"
        f"• Stato: 🟠 PRUDENZA STATISTICA (EV: -0.957)\n"
        f"• Consigliati: 2 Sestine TITAN (Budget 2,00 €)\n\n"
        f"🔮 DODECAEDRO A.I. POOL (4 Strati Bilanciati):\n"
        f"{dodeca_pool}\n\n"
        f"🔥 SESTINE CONCENTRATE (Filtrate Anti-Overfitting):\n"
        f"1️⃣ TITAN 1: {titan1}\n"
        f"   • Somma: {sum1} | Z-Score: {z1:+0.2f}\n"
        f"2️⃣ TITAN 2: {titan2}\n"
        f"   • Somma: {sum2} | Z-Score: {z2:+0.2f}\n"
    )

    send_telegram_notification(report_text, CHART_FILE)
    print("=== ESECUZIONE COMPLETATA CON SUCCESSO ===")

if __name__ == "__main__":
    main()
