import json
import os
import math
from datetime import datetime, timedelta
import itertools
import urllib.request

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
        select_vortex_sestinas_multi,
        balance_pool,
        determine_budget_mode,
    )
    VORTEX_ENGINE_AVAILABLE = True
    print("[+] Venus Vortex — Opportunity Engine: ATTIVO")
except ImportError as e:
    VORTEX_ENGINE_AVAILABLE = False
    print(f"[!] vortex_opportunity non disponibile ({e}). Fallback TITAN classico.")

# ==========================================
# VORTEX ANALYTICS (opzionale)
# ==========================================
try:
    from vortex_analytics import (
        generate_heatmap,
        run_statistical_tests,
        format_stats_for_report as format_stats_report,
    )
    ANALYTICS_AVAILABLE = True
    print("[+] Venus Vortex — Analytics: ATTIVO")
except ImportError as e:
    ANALYTICS_AVAILABLE = False
    print(f"[!] vortex_analytics non disponibile ({e})")

# ==========================================
# VENUS TRACK RECORD (opzionale)
# ==========================================
try:
    from venus_track_record import (
        record_predictions,
        update_with_result,
        detect_wins,
        format_win_notification,
        get_stats as get_track_stats,
        format_stats_for_report as format_track_report,
    )
    TRACK_AVAILABLE = True
    print("[+] Venus Vortex — Track Record: ATTIVO")
except ImportError as e:
    TRACK_AVAILABLE = False
    print(f"[!] venus_track_record non disponibile ({e})")

# ==========================================
# TRUE MIMIC GENERATOR (opzionale)
# ==========================================
try:
    from true_mimic_generator import (
        extract_fingerprints,
        validate_sestina,
    )
    MIMIC_AVAILABLE = True
    print("[+] Venus Vortex — True Mimic: ATTIVO")
except ImportError as e:
    MIMIC_AVAILABLE = False
    print(f"[!] true_mimic_generator non disponibile ({e})")

# ==========================================
# PERSONAL STATS (opzionale)
# ==========================================
try:
    from personal_stats import (
        analyze_played,
        format_personal_report,
    )
    PERSONAL_AVAILABLE = True
    print("[+] Venus Vortex — Personal Stats: ATTIVO")
except ImportError as e:
    PERSONAL_AVAILABLE = False
    print(f"[!] personal_stats non disponibile ({e})")

# ==========================================
# COSTANTI E CONFIGURAZIONE DI SISTEMA
# ==========================================
HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"
HEATMAP_FILE = "vortex_heatmap.png"
DISTRIBUTION_FILE = "vortex_distribution.png"
JACKPOT_FILE = "venus_jackpot.json"
MANUAL_OVERRIDE_FILE = "venus_manual_override.json"

# URL pubblici
DASHBOARD_URL = "https://francis490.github.io/superenalotto-venus-vortex/"
ANALYTICS_URL = "https://francis490.github.io/superenalotto-venus-vortex/analysis.html"

GAUSS_MEAN = 273.0
GAUSS_STD = 43.5

DEFAULT_JACKPOT = 26500000

SUPERENALOTTO_WEEKDAYS = {1, 3, 4, 5}

# Limite caption Telegram per sendPhoto
TELEGRAM_CAPTION_LIMIT = 1000

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
# 3-bis. HELPER PER DATA E 2026 (FIX)
# ==========================================
def sort_history_by_date(history):
    """Ordina lo storico per DATA (non per numero concorso)."""
    def _key(item):
        try:
            dt = datetime.strptime(str(item.get("data", "")), "%d/%m/%Y")
            return (dt.year, dt.month, dt.day)
        except (ValueError, TypeError):
            return (0, 0, 0)
    return sorted(history, key=_key)


def find_last_2026_draw(history):
    """
    Trova l'ultima estrazione del 2026 (concorso 1-999).
    Ignora i concorsi 2025 che hanno offset +1000.
    """
    candidates = [h for h in history
                  if isinstance(h.get("concorso"), int)
                  and 1 <= h["concorso"] <= 999]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x["concorso"])

# ==========================================
# 4. GENERAZIONE GRAFICO PRINCIPALE
# ==========================================
def generate_vortex_chart(all_sestinas, dodeca_pool, scores):
    plt.rcParams['text.color'] = '#f1e8ff'
    plt.rcParams['axes.labelcolor'] = '#f1e8ff'
    plt.rcParams['xtick.color'] = '#a89bbd'
    plt.rcParams['ytick.color'] = '#a89bbd'

    fig = plt.figure(figsize=(14, 8), facecolor='#0a0612')

    ax1 = fig.add_subplot(2, 2, (1, 3), facecolor='#150b1f')
    x = np.linspace(100, 440, 500)
    y = norm.pdf(x, GAUSS_MEAN, GAUSS_STD)
    ax1.plot(x, y, color='#c026d3', linewidth=2.5, label='Gaussiana Teorica')

    colors = ['#ec4899', '#06b6d4', '#fbbf24', '#10b981', '#8b5cf6', '#f97316']
    for i, sestina in enumerate(all_sestinas):
        s_sum = sum(sestina)
        color = colors[i % len(colors)]
        ax1.axvline(s_sum, color=color, linestyle='--', linewidth=2,
                    label=f'Vortex {i+1} (Somma {s_sum})')

    if not all_sestinas:
        ax1.text(0.5, 0.5, "SKIP MODE — Nessuna sestina",
                 transform=ax1.transAxes, ha='center', va='center',
                 fontsize=14, color='#f87171', fontweight='bold')

    ax1.set_title("Distribuzione Gaussiana — Punti di Equilibrio",
                  fontsize=12, fontweight='bold', color='#10b981')
    ax1.legend(facecolor='#150b1f', edgecolor='#c026d3', fontsize=8)

    ax2 = fig.add_subplot(2, 2, 2, facecolor='#150b1f')
    dodeca_scores = [scores.get(n, 1.0) for n in dodeca_pool]
    ax2.bar([str(n) for n in dodeca_pool], dodeca_scores,
            color='#06b6d4', edgecolor='#150b1f')
    ax2.set_title("Vortex Numerical Field — Ranking Energetico",
                  fontsize=10, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    ax3 = fig.add_subplot(2, 2, 4, facecolor='#150b1f')
    if all_sestinas:
        n = len(all_sestinas)
        matrix_data = np.zeros((n, 6))
        for i, sestina in enumerate(all_sestinas):
            matrix_data[i, :] = sestina
        ax3.matshow(matrix_data, cmap='plasma')
        ax3.xaxis.tick_top()
        ax3.set_yticks(range(n))
        ax3.set_yticklabels([f'Vortex {i+1}' for i in range(n)],
                            fontweight='bold', fontsize=8)
        ax3.set_xticks(range(6))
        ax3.set_xticklabels([f'Pos {i+1}' for i in range(6)])
        for i in range(n):
            for j in range(6):
                val = int(matrix_data[i, j])
                ax3.text(j, i, str(val), va='center', ha='center',
                         color='white', fontweight='bold', fontsize=10)
        ax3.set_title("Matrice di Copertura Armonica",
                      fontsize=10, fontweight='bold', pad=20)
    else:
        ax3.axis('off')
        ax3.text(0.5, 0.5, "SKIP MODE",
                 transform=ax3.transAxes, ha='center', va='center',
                 fontsize=16, color='#f87171', fontweight='bold')

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

# ==========================================
# 4-bis. GRAFICO DISTRIBUZIONE
# ==========================================
def generate_distribution_chart(history):
    if not history or len(history) < 10:
        return None

    sums = []
    for d in history:
        comb = d.get("combinazione", [])
        if len(comb) == 6:
            sums.append(sum(comb))

    if not sums:
        return None

    decades = [0] * 9
    for d in history:
        for n in d.get("combinazione", []):
            if 1 <= n <= 90:
                decades[min(8, (n - 1) // 10)] += 1

    parity = [0] * 7
    for d in history:
        comb = d.get("combinazione", [])
        if len(comb) == 6:
            n_pari = sum(1 for n in comb if n % 2 == 0)
            parity[n_pari] += 1

    plt.rcParams['text.color'] = '#f1e8ff'
    plt.rcParams['axes.labelcolor'] = '#f1e8ff'
    plt.rcParams['xtick.color'] = '#a89bbd'
    plt.rcParams['ytick.color'] = '#a89bbd'

    fig = plt.figure(figsize=(14, 8), facecolor='#0a0612')

    ax1 = fig.add_subplot(2, 2, 1, facecolor='#150b1f')
    ax1.hist(sums, bins=15, color='#c026d3',
             edgecolor='#150b1f', alpha=0.8)
    ax1.axvline(GAUSS_MEAN, color='#fbbf24', linestyle='--',
                linewidth=2, label=f'Media teorica ({int(GAUSS_MEAN)})')
    mean_obs = sum(sums) / len(sums)
    ax1.axvline(mean_obs, color='#06b6d4', linestyle='-',
                linewidth=2, label=f'Media oss. ({mean_obs:.1f})')
    ax1.set_title("Distribuzione Somme", fontsize=11,
                  fontweight='bold', color='#10b981')
    ax1.legend(facecolor='#150b1f', edgecolor='#c026d3', fontsize=8)
    ax1.set_xlabel("Somma", fontsize=9)
    ax1.set_ylabel("Frequenza", fontsize=9)

    ax2 = fig.add_subplot(2, 2, 2, facecolor='#150b1f')
    labels_dec = ["1-9", "10-19", "20-29", "30-39", "40-49",
                  "50-59", "60-69", "70-79", "80-90"]
    ax2.bar(labels_dec, decades, color='#06b6d4', edgecolor='#150b1f')
    expected = len(history) * 6 / 9
    ax2.axhline(expected, color='#fbbf24', linestyle='--',
                linewidth=1.5, label=f'Attesa ({expected:.0f})')
    ax2.set_title("Frequenza per Decade", fontsize=11,
                  fontweight='bold', color='#10b981')
    ax2.legend(facecolor='#150b1f', edgecolor='#c026d3', fontsize=8)
    ax2.tick_params(axis='x', rotation=45)
    ax2.set_ylabel("Occorrenze", fontsize=9)

    ax3 = fig.add_subplot(2, 2, 3, facecolor='#150b1f')
    labels_par = [f"{i}P / {6-i}D" for i in range(7)]
    colors_par = ['#ec4899' if i in (2, 3, 4) else '#a855f7'
                  for i in range(7)]
    ax3.bar(labels_par, parity, color=colors_par, edgecolor='#150b1f')
    ax3.set_title("Distribuzione Parità (Pari/Dispari)", fontsize=11,
                  fontweight='bold', color='#10b981')
    ax3.tick_params(axis='x', rotation=45)
    ax3.set_ylabel("Occorrenze", fontsize=9)

    ax4 = fig.add_subplot(2, 2, 4, facecolor='#150b1f')
    ax4.axis('off')

    try:
        import statistics
        mean_val = statistics.mean(sums)
        stdev_val = statistics.stdev(sums) if len(sums) > 1 else 0
    except Exception:
        mean_val = sum(sums) / len(sums) if sums else 0
        stdev_val = 0

    exp_dec = len(history) * 6 / 9
    chi2 = sum((obs - exp_dec) ** 2 / exp_dec for obs in decades) if exp_dec > 0 else 0

    stats_text = (
        f"Concorsi analizzati:  {len(history)}\n"
        f"Somme analizzate:     {len(sums)}\n"
        f"Somma media (oss.):   {mean_val:.2f}\n"
        f"Somma media (teor.):  273.00\n"
        f"Dev. std (oss.):      {stdev_val:.2f}\n"
        f"Dev. std (teor.):     43.50\n"
        f"Somma min:            {min(sums)}\n"
        f"Somma max:            {max(sums)}\n\n"
        f"Chi² decadi:          {chi2:.2f}\n"
        f"Chi² critico (df=8):  15.51\n"
        f"{'✓ Uniforme' if chi2 < 15.51 else '⚠ Deviazione'}"
    )

    ax4.text(0.05, 0.95, stats_text,
             transform=ax4.transAxes,
             fontsize=11,
             fontfamily='monospace',
             verticalalignment='top',
             color='#f1e8ff',
             bbox=dict(boxstyle='round',
                       facecolor='#0a0612',
                       edgecolor='#c026d3',
                       alpha=0.6))

    ax4.set_title("Statistiche Descrittive", fontsize=11,
                  fontweight='bold', color='#10b981')

    plt.tight_layout()
    plt.savefig(DISTRIBUTION_FILE, dpi=200,
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

    print(f"[+] Grafico distribuzione salvato: {DISTRIBUTION_FILE}")
    return DISTRIBUTION_FILE

# ==========================================
# 5. NOTIFICA TELEGRAM
# ==========================================
def send_telegram_photo(photo_path, caption=""):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("[!] Token mancanti. Invio saltato.")
        return

    if not os.path.exists(photo_path):
        print(f"[!] File non trovato: {photo_path}")
        return

    if caption and len(caption) > TELEGRAM_CAPTION_LIMIT:
        caption = caption[:TELEGRAM_CAPTION_LIMIT - 3] + "..."

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    try:
        with open(photo_path, "rb") as image_file:
            image_bytes = image_file.read()

        boundary = "----VenusVortexBoundary7MA4YWxkTrZu0gW"
        filename = os.path.basename(photo_path)

        body = bytearray()
        body += f"--{boundary}\r\n".encode("utf-8")
        body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        body += f"{chat_id}\r\n".encode("utf-8")

        if caption:
            body += f"--{boundary}\r\n".encode("utf-8")
            body += b'Content-Disposition: form-data; name="caption"\r\n'
            body += b"Content-Type: text/html; charset=utf-8\r\n\r\n"
            body += caption.encode("utf-8")
            body += b"\r\n"

            body += f"--{boundary}\r\n".encode("utf-8")
            body += b'Content-Disposition: form-data; name="parse_mode"\r\n\r\n'
            body += b"HTML\r\n"

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
            print(f"[+] Foto inviata: {filename} ({response.status})")

    except Exception as e:
        print(f"[!] Errore invio foto {photo_path}: {e}")


def send_telegram_message(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("[!] Token mancanti. Messaggio saltato.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    if len(text) > 4000:
        text = text[:3997] + "..."

    try:
        import urllib.parse
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "false",
        }).encode("utf-8")

        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")

        with urllib.request.urlopen(req, timeout=30) as response:
            print(f"[+] Messaggio Telegram inviato! ({response.status})")
    except Exception as e:
        print(f"[!] Errore invio messaggio: {e}")

# ==========================================
# 6. COSTRUZIONE DATABASE PER L'HTML
# ==========================================
def build_database_payload(history, dodeca_pool, all_sestinas,
                           next_concorso, budget_mode):
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # FIX: usa l'ultima estrazione 2026 (non il concorso 1208 del 2025)
    last_draw_2026 = find_last_2026_draw(history)
    last_draw = last_draw_2026 if last_draw_2026 else (history[-1] if history else {})

    last_comb = last_draw.get("combinazione", []) or []
    last_concorso = last_draw.get("concorso", "N/A")
    last_date = last_draw.get("data", "N/A")
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

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

    vortex_data = {}
    ev_data = {}
    if VORTEX_ENGINE_AVAILABLE and jackpot_value > 0:
        try:
            ev_data = calculate_ev(jackpot_value)
            rollover_data = rollover_status(jackpot_value)
            bt_data = None
            if len(all_sestinas) >= 2:
                bt_data = backtest(history, all_sestinas[0], all_sestinas[1],
                                   last_n=30)
            elif len(all_sestinas) == 1:
                bt_data = backtest(history, all_sestinas[0], all_sestinas[0],
                                   last_n=30)
            vortex_data = {
                "ev": ev_data,
                "rollover": rollover_data,
                "backtest": bt_data,
            }
        except Exception as e:
            print(f"[!] Errore VORTEX analysis: {e}")

    titan_predictions = []
    for i, sestina in enumerate(all_sestinas):
        s_sum = sum(sestina)
        s_z = round((s_sum - GAUSS_MEAN) / GAUSS_STD, 2)
        sig = "—"
        if VORTEX_ENGINE_AVAILABLE:
            try:
                sig = vortex_signature(sestina, next_concorso,
                                       datetime.now().strftime("%d/%m/%Y"))
            except Exception:
                pass
        titan_predictions.append({
            "id": f"VORTEX {i + 1}",
            "numbers": sestina,
            "sum": s_sum,
            "z_score": s_z,
            "confidence": estimate_confidence(s_z),
            "ev_score": 1.0,
            "signature": sig,
        })

    ev_for_risk = ev_data.get("ev_total", -0.957) if ev_data else -0.957

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
            "ev": ev_for_risk,
            "level": "PRUDENTE (Reset Post-Vincita Jackpot)",
            "advice": budget_mode.get("message", "Budget base 2 sestine."),
        },
        "budget_mode": budget_mode,
        "dodeca_pool": dodeca_pool,
        "titan_predictions": titan_predictions,
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

    # === OVERRIDE MANUALE ===
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
                    history = sort_history_by_date(history)
                    save_json(HISTORY_FILE, history)
                    print(f"[+] OVERRIDE: aggiunto concorso {manual_concorso}")
                else:
                    print(f"[*] Override: concorso {manual_concorso} già presente.")
            else:
                print("[*] Override manuale: nessuna estrazione valida.")
        except Exception as e:
            print(f"[!] Errore override manuale: {e}")

    # === ORDINA E IDENTIFICA ULTIMA 2026 ===
    history = sort_history_by_date(history)
    last_2026 = find_last_2026_draw(history)
    if last_2026:
        print(f"[+] Ultima estrazione 2026: concorso {last_2026['concorso']} "
              f"del {last_2026.get('data', 'N/A')}")

    raw_scores, delays, frequencies = calculate_raw_scores(history)
    adjusted_scores = apply_cooldown_factor(raw_scores, history)
    dodeca_pool = build_tiered_dodecahedron(adjusted_scores, delays, history)

    if VORTEX_ENGINE_AVAILABLE:
        try:
            dodeca_pool = balance_pool(dodeca_pool)
            print(f"[+] Pool bilanciato (4/4/4): {dodeca_pool}")
        except Exception as e:
            print(f"[!] Errore bilanciamento pool: {e}")

    jackpot_for_mode = DEFAULT_JACKPOT
    if os.path.exists(MANUAL_OVERRIDE_FILE):
        try:
            with open(MANUAL_OVERRIDE_FILE, "r", encoding="utf-8") as mf:
                mdata = json.load(mf)
                if isinstance(mdata.get("jackpot"), int) and mdata["jackpot"] > 0:
                    jackpot_for_mode = mdata["jackpot"]
        except Exception:
            pass

    budget_mode = {
        "mode": "NORMALE", "emoji": "🟡", "n_sestinas": 2,
        "cost_eur": 2.0, "ev": 0.0,
        "message": "EV neutro. 2 sestine (budget base)."
    }
    if VORTEX_ENGINE_AVAILABLE:
        try:
            budget_mode = determine_budget_mode(jackpot_for_mode)
            print(f"[+] Budget mode: {budget_mode['emoji']} {budget_mode['mode']} "
                  f"({budget_mode['n_sestinas']} sestine · {budget_mode['cost_eur']}€)")
        except Exception as e:
            print(f"[!] Errore budget mode: {e}")

    n_sestinas = int(budget_mode.get("n_sestinas", 2))
    skip_mode = (n_sestinas == 0)

    all_sestinas = []

    if skip_mode:
        print("[*] BUDGET MODE = SKIP: nessuna sestina generata.")
    else:
        if VORTEX_ENGINE_AVAILABLE:
            try:
                vortex_sel = select_vortex_sestinas_multi(
                    dodeca_pool, adjusted_scores, history, n_sestinas=n_sestinas
                )
                all_sestinas = [list(s[0]) for s in vortex_sel]
                print(f"[+] {len(all_sestinas)} sestine selezionate con VORTEX ENGINE")
            except Exception as e:
                print(f"[!] Errore VORTEX multi: {e}. Fallback a 2 sestine.")
                vortex_sel = select_vortex_sestinas(dodeca_pool, adjusted_scores,
                                                    history, top_n=2)
                all_sestinas = [list(vortex_sel[0][0])]
                if len(vortex_sel) > 1:
                    all_sestinas.append(list(vortex_sel[1][0]))
        else:
            t1, t2 = select_titan_sestinas(dodeca_pool, adjusted_scores, history)
            all_sestinas = [t1, t2]
            print("[*] Sestine selezionate con TITAN classico (fallback)")

    # === VALIDAZIONE FINGERPRINT ===
    if MIMIC_AVAILABLE and all_sestinas:
        try:
            fp = extract_fingerprints(history)
            for i, s in enumerate(all_sestinas, 1):
                ok, score, checks = validate_sestina(s, fp)
                status = "OK" if ok else "PARZIALE"
                passed = int(round(score * 12))
                print(f"[+] Sestina {i}: {status} - {passed}/12 fingerprint")
        except Exception as e:
            print(f"[!] Validazione fingerprint saltata: {e}")

    titan1 = all_sestinas[0] if all_sestinas else []
    titan2 = all_sestinas[1] if len(all_sestinas) > 1 else titan1

    sum1 = sum(titan1) if titan1 else 0
    sum2 = sum(titan2) if titan2 else 0
    z1 = round((sum1 - GAUSS_MEAN) / GAUSS_STD, 2) if titan1 else 0
    z2 = round((sum2 - GAUSS_MEAN) / GAUSS_STD, 2) if titan2 else 0

    # === ULTIMA ESTRAZIONE 2026 (non 1208) ===
    last_draw = last_2026 if last_2026 else (history[-1] if history else {})
    last_concorso = last_draw.get("concorso", "N/A")
    last_comb = last_draw.get("combinazione") or []
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

    try:
        next_concorso = int(last_concorso) + 1
    except (ValueError, TypeError):
        next_concorso = 150

    next_date_str = calculate_next_draw_date(last_draw.get("data", "N/A"))

    # === TRACK RECORD: registra sestine generate ===
    if TRACK_AVAILABLE and all_sestinas:
        try:
            record_predictions(next_concorso, all_sestinas,
                               budget_mode.get("mode", "NORMALE"))
        except Exception as e:
            print(f"[!] Errore track record: {e}")

    # === TRACK RECORD: aggiorna + rileva vincite ===
    win_info = None
    if TRACK_AVAILABLE and last_draw and last_draw.get("combinazione"):
        try:
            update_with_result(
                last_draw.get("concorso"),
                last_draw.get("combinazione")
            )
            win_info = detect_wins(
                last_draw.get("concorso"),
                last_draw.get("combinazione")
            )
            if win_info:
                print(f"[!] VINCITA RILEVATA! Concorso {win_info['concorso']} "
                      f"-> {win_info['best_hits']} punti")
        except Exception as e:
            print(f"[!] Errore update track: {e}")

    # === SCRITTURA DATABASE ===
    payload = build_database_payload(
        history, dodeca_pool, all_sestinas, next_concorso, budget_mode
    )
    save_json(DATABASE_FILE, payload)

    # === GRAFICI ===
    generate_vortex_chart(all_sestinas, dodeca_pool, adjusted_scores)

    dist_path = None
    try:
        dist_path = generate_distribution_chart(history)
    except Exception as e:
        print(f"[!] Errore grafico distribuzione: {e}")

    heatmap_path = None
    if ANALYTICS_AVAILABLE:
        try:
            heatmap_path = generate_heatmap(history)
        except Exception as e:
            print(f"[!] Errore heatmap: {e}")

    # === STATISTICHE ===
    stats_block = "—"
    if ANALYTICS_AVAILABLE:
        try:
            stats_results = run_statistical_tests(history)
            stats_block = format_stats_report(stats_results)
        except Exception as e:
            print(f"[!] Errore test statistici: {e}")

    # === PERSONAL STATS ===
    personal_block = "—"
    if PERSONAL_AVAILABLE:
        try:
            personal_stats = analyze_played()
            personal_block = format_personal_report(personal_stats)
        except Exception as e:
            print(f"[!] Errore personal stats: {e}")
            personal_block = "📊 <b>STATISTICHE PERSONALI</b>\n\nErrore nel calcolo."

    track_block = "—"
    if TRACK_AVAILABLE:
        try:
            track_stats = get_track_stats()
            track_block = format_track_report(track_stats)
        except Exception as e:
            print(f"[!] Errore track stats: {e}")

    # === REPORT TELEGRAM ===
    jackpot_for_report = payload.get("next_contest", {}).get("jackpot", DEFAULT_JACKPOT)
    vortex_data = payload.get("vortex", {})
    ev_data = vortex_data.get("ev", {})
    rollover_data = vortex_data.get("rollover", {})
    bt_data = vortex_data.get("backtest", {})

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

    bm = payload.get("budget_mode", {})
    bm_emoji = bm.get("emoji", "🟡")
    bm_mode = bm.get("mode", "NORMALE")
    bm_n = bm.get("n_sestinas", len(all_sestinas))
    bm_cost = bm.get("cost_eur", 2.0)
    bm_msg = bm.get("message", "")

    sestinas_lines = []
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]
    for i, sestina in enumerate(all_sestinas):
        s_sum = sum(sestina)
        s_z = round((s_sum - GAUSS_MEAN) / GAUSS_STD, 2)
        s_sig = "—"
        if VORTEX_ENGINE_AVAILABLE:
            try:
                s_sig = vortex_signature(sestina, next_concorso,
                                         datetime.now().strftime("%d/%m/%Y"))
            except Exception:
                pass
        emoji = emojis[i] if i < len(emojis) else f"{i+1}."
        sestinas_lines.append(
            f"{emoji} {sestina}\n"
            f"   • Somma: {s_sum} · Z: {s_z:+0.2f}\n"
            f"   • ✦ {s_sig}"
        )

    if skip_mode:
        sestinas_block = "🚫 SKIP MODE — Nessuna sestina da giocare."
    else:
        sestinas_block = "\n".join(sestinas_lines) if sestinas_lines else "—"

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
        f"🎛️ BUDGET MODE: {bm_emoji} {bm_mode}\n"
        f"• Sestine: {bm_n} · Costo: {bm_cost:.2f} €\n"
        f"• {bm_msg}\n\n"
        f"📊 TRACK RECORD:\n{track_block}\n\n"
        f"{personal_block}\n\n"
        f"🔬 STATISTICAL TESTS:\n{stats_block}\n\n"
        f"🔮 VORTEX NUMERICAL FIELD:\n"
        f"{dodeca_pool}\n\n"
        f"🔥 VORTEX SESTINE — Harmonic Filter:\n"
        f"{sestinas_block}\n\n"
        f"🌌 Venus Vortex — Cosmic Pattern Engine\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <a href='{ANALYTICS_URL}'>Apri Analytics Dashboard</a>\n"
        f"🏠 <a href='{DASHBOARD_URL}'>Apri Dashboard Principale</a>"
    )

    # === INVIA GRAFICO (senza caption) + REPORT (come messaggio) ===
    send_telegram_photo(CHART_FILE, "")
    send_telegram_message(report_text)

    # === INVIA HEATMAP ===
    if heatmap_path and os.path.exists(heatmap_path):
        send_telegram_photo(heatmap_path, "🔥 Vortex Heatmap — Numeri caldi/freddi")

    # === INVIA GRAFICO DISTRIBUZIONE ===
    if dist_path and os.path.exists(dist_path):
        send_telegram_photo(dist_path, "📊 Analisi Distribuzione — Somme, Decadi, Parità")

    # === INVIA MESSAGGIO LINK ===
    links_msg = (
        "📊 <b>ANALYTICS DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <a href='{ANALYTICS_URL}'>Statistiche Complete</a>\n"
        "Somme · Decadi · Parità · Pattern · Autocorrelazione\n\n"
        f"🏠 <a href='{DASHBOARD_URL}'>Dashboard Principale</a>\n"
        "Sestine · Grafici · Heatmap · Track Record"
    )
    send_telegram_message(links_msg)

    # === NOTIFICA VINCITA (URGENTE) ===
    if win_info:
        win_msg = format_win_notification(win_info)
        if win_msg:
            send_telegram_message(win_msg)
            print(f"[!] Notifica VINCITA inviata per concorso {win_info['concorso']}")

    print("=== VENUS VORTEX — COMPLETATO ===")

if __name__ == "__main__":
    main()
