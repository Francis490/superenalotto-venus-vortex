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
# VORTEX OPPORTUNITY ENGINE (opzionale)
# ==========================================
try:
    from vortex_opportunity import (
        calculate_ev,
        rollover_status,
        vortex_signature,
        backtest,
        select_vortex_sestinas,
    )
    VORTEX_ENGINE_AVAILABLE = True
    print("[+] Venus Vortex — Opportunity Engine: ATTIVO")
except ImportError as e:
    VORTEX_ENGINE_AVAILABLE = False
    print(f"[!] vortex_opportunity non disponibile ({e}). Fallback TITAN classico.")

# ==========================================
# COSTANTI E CONFIGURAZIONE DI SISTEMA
# ==========================================
HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"
JACKPOT_FILE = "venus_jackpot.json"
MANUAL_OVERRIDE_FILE = "venus_manual_override.json"
INDEX_FILE = "index.html"

GAUSS_MEAN = 273.0
GAUSS_STD = 43.5

DEFAULT_JACKPOT = 26500000  # importo in euro (int)

# Giorni settimanali del SuperEnalotto (Lun=0, Mar=1, Mer=2, Gio=3, Ven=4, Sab=5, Dom=6)
SUPERENALOTTO_WEEKDAYS = {1, 3, 4, 5}

# ==========================================
# 1. GESTIONE FILE JSON & NORMALIZZAZIONE
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
        for key in ("sestina", "combinazione", "numbers", "estratti",
                    "numeri", "numeri_estratti", "winning_numbers"):
            nums = _coerce_numbers(item.get(key))
            if len(nums) >= 6:
                clean_comb = nums[:6]
                break

        if not clean_comb:
            for _, v in item.items():
                nums = _coerce_numbers(v)
                if len(nums) >= 6:
                    clean_comb = nums[:6]
                    break

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

    for num in sorted_by_score:
        if len(dodeca_pool) < 4:
            dodeca_pool.append(num)

    medium_candidates = [n for n in range(1, 91)
                         if 5 <= delays[n] <= 15 and n not in dodeca_pool]
    medium_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in medium_candidates:
        if len(dodeca_pool) < 8:
            dodeca_pool.append(num)

    if len(dodeca_pool) < 8:
        for num in sorted_by_score:
            if num not in dodeca_pool and len(dodeca_pool) < 8:
                dodeca_pool.append(num)

    cold_candidates = [n for n in range(1, 91) if n not in dodeca_pool]
    cold_candidates.sort(key=lambda x: delays[x], reverse=True)
    for num in cold_candidates[:2]:
        dodeca_pool.append(num)

    anti_massa_candidates = [n for n in range(32, 91) if n not in dodeca_pool]
    anti_massa_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in anti_massa_candidates[:2]:
        dodeca_pool.append(num)

    while len(dodeca_pool) < 12:
        for num in sorted_by_score:
            if num not in dodeca_pool:
                dodeca_pool.append(num)
                break

    return sorted(dodeca_pool[:12])

def select_titan_sestinas(dodeca_pool, adjusted_scores, history):
    """Fallback TITAN classico (usato se vortex_opportunity non è disponibile)."""
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
# 3. CONFIDENCE / DATE
# ==========================================
def estimate_confidence(z_score):
    val = max(0.0, 25.0 - abs(z_score) * 5.0)
    return round(val, 2)

def calculate_next_draw_date(last_date_str):
    try:
        last_date = datetime.strptime(str(last_date_str), "%d/%m/%Y")
    except (ValueError, TypeError):
        last_date = datetime.now()

    candidate = last_date + timedelta(days=1)
    for _ in range(7):
        if candidate.weekday() in SUPERENALOTTO_WEEKDAYS:
            return candidate.strftime("%d/%m/%Y")
        candidate += timedelta(days=1)

    return (last_date + timedelta(days=1)).strftime("%d/%m/%Y")

# ==========================================
# 4. GENERAZIONE GRAFICO
# ==========================================
def generate_titan_chart(titan1, titan2, dodeca_pool, scores):
    plt.rcParams['text.color'] = '#f1e8ff'
    plt.rcParams['axes.labelcolor'] = '#f1e8ff'
    plt.rcParams['xtick.color'] = '#a89bbd'
    plt.rcParams['ytick.color'] = '#a89bbd'

    fig = plt.figure(figsize=(14, 8), facecolor='#0a0612')

    ax1 = fig.add_subplot(2, 2, (1, 3), facecolor='#150b1f')
    x = np.linspace(100, 440, 500)
    y = norm.pdf(x, GAUSS_MEAN, GAUSS_STD)
    ax1.plot(x, y, color='#c026d3', linewidth=2.5, label='Gaussiana Teorica')

    sum1 = sum(titan1)
    sum2 = sum(titan2)
    ax1.axvline(sum1, color='#ec4899', linestyle='--', linewidth=2,
                label=f'Vortex 1 (Somma {sum1})')
    ax1.axvline(sum2, color='#06b6d4', linestyle='--', linewidth=2,
                label=f'Vortex 2 (Somma {sum2})')
    ax1.set_title("Distribuzione Gaussiana — Punti di Equilibrio",
                  fontsize=12, fontweight='bold', color='#10b981')
    ax1.legend(facecolor='#150b1f', edgecolor='#c026d3')

    ax2 = fig.add_subplot(2, 2, 2, facecolor='#150b1f')
    dodeca_scores = [scores.get(n, 1.0) for n in dodeca_pool]
    ax2.bar([str(n) for n in dodeca_pool], dodeca_scores,
            color='#06b6d4', edgecolor='#150b1f')
    ax2.set_title("Vortex Numerical Field — Ranking Energetico",
                  fontsize=10, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    ax3 = fig.add_subplot(2, 2, 4, facecolor='#150b1f')
    matrix_data = np.zeros((2, 6))
    matrix_data[0, :] = titan1
    matrix_data[1, :] = titan2
    ax3.matshow(matrix_data, cmap='plasma')
    ax3.xaxis.tick_top()
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['Vortex 1', 'Vortex 2'], fontweight='bold')
    ax3.set_xticks(range(6))
    ax3.set_xticklabels([f'Pos {i+1}' for i in range(6)])
    for i in range(2):
        for j in range(6):
            val = int(matrix_data[i, j])
            ax3.text(j, i, str(val), va='center', ha='center',
                     color='white', fontweight='bold', fontsize=12)
    ax3.set_title("Matrice di Copertura Armonica",
                  fontsize=10, fontweight='bold', pad=20)

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

# ==========================================
# 5. NOTIFICA TELEGRAM
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

        boundary = "----VenusVortexBoundary7MA4YWxkTrZu0gW"
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

    # --- JACKPOT: priorità override manuale > fetch auto > default ---
    jackpot_value = DEFAULT_JACKPOT
    if os.path.exists(MANUAL_OVERRIDE_FILE):
        try:
            with open(MANUAL_OVERRIDE_FILE, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
                if isinstance(mdata.get("jackpot"), int) and mdata["jackpot"] > 0:
                    jackpot_value = mdata["jackpot"]
                    print(f"[+] Jackpot da OVERRIDE MANUALE: {jackpot_value:,} €")
        except Exception as e:
            print(f"[!] Errore lettura {MANUAL_OVERRIDE_FILE}: {e}")
    elif os.path.exists(JACKPOT_FILE):
        try:
            with open(JACKPOT_FILE, "r", encoding="utf-8") as jf:
                jdata = json.load(jf)
                if isinstance(jdata.get("jackpot"), int) and jdata["jackpot"] > 0:
                    jackpot_value = jdata["jackpot"]
                    print(f"[+] Jackpot letto da {JACKPOT_FILE}: {jackpot_value:,} €")
        except Exception as e:
            print(f"[!] Errore lettura {JACKPOT_FILE}: {e}. Uso DEFAULT.")

    # --- VORTEX OPPORTUNITY ANALYSIS ---
    vortex_data = {}
    if VORTEX_ENGINE_AVAILABLE and jackpot_value > 0:
        try:
            ev_data = calculate_ev(jackpot_value)
            rollover_data = rollover_status(jackpot_value)
            sig1 = vortex_signature(titan1, next_concorso,
                                    datetime.now().strftime("%d/%m/%Y"))
            sig2 = vortex_signature(titan2, next_concorso,
                                    datetime.now().strftime("%d/%m/%Y"))
            bt_data = backtest(history, titan1, titan2, last_n=30)
            vortex_data = {
                "signature_1": sig1,
                "signature_2": sig2,
                "ev": ev_data,
                "rollover": rollover_data,
                "backtest": bt_data,
            }
        except Exception as e:
            print(f"[!] Errore VORTEX analysis: {e}")

    payload = {
        "updated_at": now_str,
        "next_contest": {
            "number": next_concorso,
            "date": calculate_next_draw_date(last_date),
            "jackpot": jackpot_value,
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
            "advice": ("Mantenere puntata minima di 2 Sestine Vortex "
                       "(Budget 2,00 €)."),
        },
        "dodeca_pool": dodeca_pool,
        "titan_predictions": [
            {
                "id": "VORTEX 1",
                "numbers": titan1,
                "sum": sum1,
                "z_score": z1,
                "confidence": conf1,
                "ev_score": 1.0,
                "signature": vortex_data.get("signature_1", ""),
            },
            {
                "id": "VORTEX 2",
                "numbers": titan2,
                "sum": sum2,
                "z_score": z2,
                "confidence": conf2,
                "ev_score": 1.0,
                "signature": vortex_data.get("signature_2", ""),
            },
        ],
        "vortex": vortex_data,
    }
    return payload

# ==========================================
# 7. MAIN PIPELINE
# ==========================================
def main():
    print("=== VENUS VORTEX — COSMIC PATTERN ENGINE ===")

    raw_history = load_json(HISTORY_FILE, [])
    history = normalize_history(raw_history)

    if not history:
        print("[!] venus_history.json vuoto. Generazione dati di sicurezza...")
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

    # Override manuale dell'ultima estrazione
    if os.path.exists(MANUAL_OVERRIDE_FILE):
        try:
            with open(MANUAL_OVERRIDE_FILE, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
            manual_draw = mdata.get("last_draw", {})
            manual_concorso = manual_draw.get("concorso")
            manual_comb = manual_draw.get("combinazione", [])

            if (isinstance(manual_concorso, int) and manual_concorso > 0
                    and isinstance(manual_comb, list) and len(manual_comb) == 6
                    and all(isinstance(n, int) and 1 <= n <= 90 for n in manual_comb)):

                existing_ids = {item.get("concorso") for item in history
                                if isinstance(item.get("concorso"), int)}

                if manual_concorso not in existing_ids:
                    new_entry = {
                        "concorso": manual_concorso,
                        "data": manual_draw.get("data", "N/A"),
                        "combinazione": manual_comb,
                        "jolly": manual_draw.get("jolly"),
                        "superstar": manual_draw.get("superstar"),
                    }
                    history.append(new_entry)
                    history.sort(key=lambda x: x.get("concorso", 0))
                    save_json(HISTORY_FILE, history)
                    print(f"[+] OVERRIDE: aggiunto concorso {manual_concorso}")
                else:
                    print(f"[*] Override: concorso {manual_concorso} già presente.")
            else:
                print("[*] Override manuale: nessuna estrazione valida.")
        except Exception as e:
            print(f"[!] Errore override manuale: {e}")

    raw_scores, delays, frequencies = calculate_raw_scores(history)
    adjusted_scores = apply_cooldown_factor(raw_scores, history)
    dodeca_pool = build_tiered_dodecahedron(adjusted_scores, delays, history)

    # === SELEZIONE SESTINE ===
    if VORTEX_ENGINE_AVAILABLE:
        vortex_sel = select_vortex_sestinas(dodeca_pool, adjusted_scores, history, top_n=2)
        titan1 = list(vortex_sel[0][0])
        titan2 = list(vortex_sel[1][0]) if len(vortex_sel) > 1 else titan1
        print("[+] Sestine selezionate con VORTEX ENGINE (anti-crowd)")
    else:
        titan1, titan2 = select_titan_sestinas(dodeca_pool, adjusted_scores, history)
        print("[*] Sestine selezionate con TITAN classico (fallback)")

    sum1, sum2 = sum(titan1), sum(titan2)
    z1 = round((sum1 - GAUSS_MEAN) / GAUSS_STD, 2)
    z2 = round((sum2 - GAUSS_MEAN) / GAUSS_STD, 2)

    last_draw = history[-1] if history else {}
    last_concorso = last_draw.get("concorso", "N/A")
    last_comb = last_draw.get("combinazione") or []
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

    try:
        next_concorso = int(last_concorso) + 1
    except (ValueError, TypeError):
        next_concorso = 148

    next_date_str = calculate_next_draw_date(last_draw.get("data", "N/A"))

    # === SCRITTURA DATABASE ===
    payload = build_database_payload(
        history, dodeca_pool, titan1, titan2, sum1, sum2, z1, z2, next_concorso
    )
    save_json(DATABASE_FILE, payload)

    # === GRAFICO ===
    generate_titan_chart(titan1, titan2, dodeca_pool, adjusted_scores)

    # === REPORT TELEGRAM ===
    jackpot_for_report = payload.get("next_contest", {}).get("jackpot", DEFAULT_JACKPOT)
    vortex_data = payload.get("vortex", {})
    ev_data = vortex_data.get("ev", {})
    rollover_data = vortex_data.get("rollover", {})
    bt_data = vortex_data.get("backtest", {})
    sig1 = vortex_data.get("signature_1", "—")
    sig2 = vortex_data.get("signature_2", "—")

    ev_line = "—"
    if ev_data:
        ev_line = f"{ev_data.get('ev_total', 0):+.4f} € · {ev_data.get('recommendation', '—')}"

    rollover_line = "—"
    if rollover_data:
        rollover_line = f"{rollover_data.get('emoji', '')} {rollover_data.get('level', '—')}"

    bt_line = "—"
    if bt_data and bt_data.get("total", 0) > 0:
        bt_line = (f"{bt_data.get('hit_rate_3plus', 0)}% "
                   f"(baseline {bt_data.get('baseline_expected', 0)}%)")

    report_text = (
        f"🌪️ VENUS VORTEX — COSMIC ANALYSIS 🌪️\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 TARGET: Concorso N° {next_concorso}\n"
        f"📅 {next_date_str} · ore 20:00\n"
        f"💰 Jackpot: € {jackpot_for_report:,}\n\n"
        f"📊 ULTIMO RISULTATO (N° {last_concorso}):\n"
        f"Sestina: {last_comb}\n"
        f"Jolly: {last_jolly} | SuperStar: {last_superstar}\n\n"
        f"⚡ OPPORTUNITY ENGINE:\n"
        f"• EV: {ev_line}\n"
        f"• Rollover: {rollover_line}\n"
        f"• Backtest: {bt_line}\n\n"
        f"🛡️ COSMIC RISK SHIELD:\n"
        f"• Budget: 2,00 € · 2 sestine\n"
        f"• Stato: PRUDENZA STATISTICA\n\n"
        f"🔮 VORTEX NUMERICAL FIELD:\n"
        f"{dodeca_pool}\n\n"
        f"🔥 VORTEX SESTINE — Harmonic Filter:\n"
        f"1️⃣ {titan1}\n"
        f"   • Somma: {sum1} · Z: {z1:+0.2f}\n"
        f"   • ✦ {sig1}\n"
        f"2️⃣ {titan2}\n"
        f"   • Somma: {sum2} · Z: {z2:+0.2f}\n"
        f"   • ✦ {sig2}\n\n"
        f"🌌 Venus Vortex — Cosmic Pattern Engine"
    )

    send_telegram_notification(report_text, CHART_FILE)
    print("=== VENUS VORTEX — COMPLETATO ===")

if __name__ == "__main__":
    main()
