"""
scraper.py
VENUS VORTEX — Cosmic Pattern Engine
Orchestratore principale (TITAN Engine).

FIX (2026-10-05):
- detect_wins ora viene chiamato PRIMA di update_with_result.
  Prima era il contrario, quindi result era già settato e
  detect_wins ritornava sempre None -> nessuna notifica di vincita.
- Rimosso venus_jackpot.json: il jackpot è gestito SOLO da
  venus_manual_override.json. Il fetch automatico era rotto.

FIX (2026-10-01):
- Generazione sestina da pool 1-90 (non più dodeca 12 numeri).
- n_sestinas forzato a 1 (tranne SKIP mode).
"""
import json
import os
import math
import urllib.request
import urllib.parse
import itertools
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from venus_utils import (
    load_json as _load_json_util,
    save_json,
    parse_date,
    sort_history_by_date,
    SUM_HARD_MIN,
    SUM_HARD_MAX,
)

# ==========================================
# VORTEX OPPORTUNITY ENGINE
# ==========================================
try:
    from vortex_opportunity import (
        calculate_ev,
        rollover_status,
        vortex_signature,
        backtest,
        select_vortex_sestinas,
        select_vortex_sestinas_multi,
        determine_budget_mode,
    )
    VORTEX_ENGINE_AVAILABLE = True
    print("[+] Venus Vortex — Opportunity Engine: ATTIVO")
except ImportError as e:
    VORTEX_ENGINE_AVAILABLE = False
    print(f"[!] vortex_opportunity non disponibile ({e}).")

# ==========================================
# VORTEX ANALYTICS
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
# VENUS TRACK RECORD
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
# PERSONAL STATS
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
# COSTANTI
# ==========================================
HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"
HEATMAP_FILE = "vortex_heatmap.png"
DISTRIBUTION_FILE = "vortex_distribution.png"
MANUAL_OVERRIDE_FILE = "venus_manual_override.json"

DASHBOARD_URL = "https://francis490.github.io/superenalotto-venus-vortex/"
ANALYTICS_URL = "https://francis490.github.io/superenalotto-venus-vortex/analysis.html"

GAUSS_MEAN = 273.0
GAUSS_STD = 43.5

DEFAULT_JACKPOT = 26500000

SUPERENALOTTO_WEEKDAYS = {1, 3, 4, 5}

TELEGRAM_CAPTION_LIMIT = 1000
TELEGRAM_MESSAGE_LIMIT = 4000
TELEGRAM_SPLIT_THRESHOLD = 3500


# ==========================================
# 1. GESTIONE JSON & NORMALIZZAZIONE
# ==========================================
def load_json(filepath, default_value):
    return _load_json_util(filepath, default_value)


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
# 2. CONFIGURAZIONE RUNTIME
# ==========================================
def read_runtime_config():
    """
    Legge la configurazione da venus_manual_override.json.

    Il jackpot è gestito SOLO da questo file. Non c'è più
    fallback su venus_jackpot.json (rimosso).
    """
    config = {
        "jackpot": None,
        "override_last_draw": None,
        "source": "default",
    }

    if os.path.exists(MANUAL_OVERRIDE_FILE):
        try:
            mdata = load_json(MANUAL_OVERRIDE_FILE, {})
            if isinstance(mdata.get("jackpot"), int) and mdata["jackpot"] > 0:
                config["jackpot"] = mdata["jackpot"]
                config["source"] = "manual_override"
                print(f"[+] Config: jackpot da OVERRIDE = "
                      f"{config['jackpot']:,} €")
            if isinstance(mdata.get("last_draw"), dict):
                config["override_last_draw"] = mdata["last_draw"]
                print(f"[+] Config: override last_draw presente "
                      f"(concorso {config['override_last_draw'].get('concorso')})")
        except Exception as e:
            print(f"[!] Errore lettura {MANUAL_OVERRIDE_FILE}: {e}")

    if config["jackpot"] is None:
        config["jackpot"] = DEFAULT_JACKPOT
        config["source"] = "default"
        print(f"[!] Config: uso jackpot DEFAULT = {config['jackpot']:,} €")

    return config


def consume_manual_override(remaining_jackpot=None):
    try:
        payload = {}
        if isinstance(remaining_jackpot, int) and remaining_jackpot > 0:
            payload["jackpot"] = remaining_jackpot
        payload["last_draw"] = None
        payload["note"] = (
            f"last_draw consumato il {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        with open(MANUAL_OVERRIDE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"[+] Override consumato: last_draw rimosso")
    except Exception as e:
        print(f"[!] Errore consumo override: {e}")


# ==========================================
# 3. HELPER DATE
# ==========================================
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


def find_last_2026_draw(history):
    candidates = [h for h in history
                  if isinstance(h.get("concorso"), int)
                  and 1 <= h["concorso"] <= 999]
    if not candidates:
        return None
    return max(candidates, key=lambda x: x["concorso"])


def estimate_confidence(z_score):
    val = max(0.0, 25.0 - abs(z_score) * 5.0)
    return round(val, 2)


# ==========================================
# 4. DODECA POOL (solo per grafico)
# ==========================================
def build_dodeca_pool_for_chart(history):
    freq = {i: 0 for i in range(1, 91)}
    for d in history[-30:]:
        for n in d.get("combinazione", []):
            if 1 <= n <= 90:
                freq[n] += 1

    sorted_nums = sorted(range(1, 91), key=lambda x: freq[x], reverse=True)
    pool = sorted_nums[:12]
    return sorted(pool)


# ==========================================
# 5. GRAFICI
# ==========================================
def generate_vortex_chart(all_sestinas, dodeca_pool, scores=None):
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
    ax2.bar([str(n) for n in dodeca_pool],
            [1.0] * len(dodeca_pool),
            color='#06b6d4', edgecolor='#150b1f')
    ax2.set_title("Vortex Numerical Field (top 12 hot)",
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
        ax3.set_title("Matrice Sestina",
                      fontsize=10, fontweight='bold', pad=20)
    else:
        ax3.axis('off')
        ax3.text(0.5, 0.5, "SKIP MODE",
                 transform=ax3.transAxes, ha='center', va='center',
                 fontsize=16, color='#f87171', fontweight='bold')

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, facecolor=fig.get_facecolor(),
                edgecolor='none')
    plt.close()


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
    chi2 = sum((obs - exp_dec) ** 2 / exp_dec
               for obs in decades) if exp_dec > 0 else 0

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
# 6. TELEGRAM
# ==========================================
def send_telegram_photo(photo_path, caption=""):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("[!] Token mancanti. Invio saltato.")
        return False

    if not os.path.exists(photo_path):
        print(f"[!] File non trovato: {photo_path}")
        return False

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
            return True

    except Exception as e:
        print(f"[!] Errore invio foto {photo_path}: {e}")
        return False


def send_telegram_message(text):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        print("[!] Token mancanti. Messaggio saltato.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    if len(text) > TELEGRAM_MESSAGE_LIMIT:
        text = text[:TELEGRAM_MESSAGE_LIMIT - 3] + "..."

    try:
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
            return True
    except Exception as e:
        print(f"[!] Errore invio messaggio: {e}")
        return False


def send_telegram_report_smart(report_text):
    if len(report_text) <= TELEGRAM_SPLIT_THRESHOLD:
        return send_telegram_message(report_text)

    mid = len(report_text) // 2
    split_pos = report_text.rfind("\n\n", 0, mid + 500)
    if split_pos < 1000:
        split_pos = mid

    part1 = report_text[:split_pos].rstrip()
    part2 = report_text[split_pos:].lstrip()

    print(f"[*] Report splittato: {len(part1)} + {len(part2)} char")

    ok1 = send_telegram_message(part1)
    ok2 = send_telegram_message(part2)
    return ok1 and ok2


# ==========================================
# 7. DATABASE PAYLOAD
# ==========================================
def build_database_payload(history, dodeca_pool, all_sestinas,
                           next_concorso, budget_mode, config):
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    last_draw_2026 = find_last_2026_draw(history)
    last_draw = last_draw_2026 if last_draw_2026 else (history[-1] if history else {})

    last_comb = last_draw.get("combinazione", []) or []
    last_concorso = last_draw.get("concorso", "N/A")
    last_date = last_draw.get("data", "N/A")
    last_jolly = last_draw.get("jolly", "N/A")
    last_superstar = last_draw.get("superstar", "N/A")

    jackpot_value = config["jackpot"]

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
                bt_data = backtest(history, all_sestinas[0], None, last_n=30)
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
            "signature": sig,
        })

    ev_for_risk = ev_data.get("ev_total") if ev_data else None

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
            "level": "PRUDENTE",
            "advice": budget_mode.get("message", ""),
        },
        "budget_mode": budget_mode,
        "dodeca_pool": dodeca_pool,
        "titan_predictions": titan_predictions,
        "vortex": vortex_data,
    }
    return payload


# ==========================================
# 8. MAIN
# ==========================================
def main():
    print("=== VENUS VORTEX — COSMIC PATTERN ENGINE ===")

    config = read_runtime_config()

    raw_history = load_json(HISTORY_FILE, [])
    history = normalize_history(raw_history)

    if not history:
        print("[!] venus_history.json vuoto. Interrompo.")
        return

    # === OVERRIDE MANUALE ===
    if config.get("override_last_draw"):
        try:
            manual_draw = config["override_last_draw"]
            manual_concorso = manual_draw.get("concorso")
            manual_comb = manual_draw.get("combinazione", [])

            if (isinstance(manual_concorso, int) and manual_concorso > 0
                    and isinstance(manual_comb, list) and len(manual_comb) == 6
                    and all(isinstance(n, int) and 1 <= n <= 90
                            for n in manual_comb)):

                existing_ids = {item.get("concorso") for item in history
                                if isinstance(item.get("concorso"), int)}

                if manual_concorso not in existing_ids:
                    new_entry = {
                        "concorso": manual_concorso,
                        "data": manual_draw.get("data", "N/A"),
                        "combinazione": manual_comb,
                        "jolly": manual_draw.get("jolly"),
                        "superstar": manual_draw.get("superstar"),
                        "sestina": manual_comb,
                    }
                    history.append(new_entry)
                    history = sort_history_by_date(history)
                    save_json(HISTORY_FILE, history)
                    print(f"[+] OVERRIDE: aggiunto concorso {manual_concorso}")

                consume_manual_override(
                    remaining_jackpot=config.get("jackpot")
                )
            else:
                print("[*] Override manuale: nessuna estrazione valida.")
        except Exception as e:
            print(f"[!] Errore override manuale: {e}")

    history = sort_history_by_date(history)
    last_2026 = find_last_2026_draw(history)
    if last_2026:
        print(f"[+] Ultima estrazione 2026: concorso {last_2026['concorso']} "
              f"del {last_2026.get('data', 'N/A')}")

    # === DODECA POOL (solo per grafico) ===
    dodeca_pool = build_dodeca_pool_for_chart(history)
    print(f"[+] Dodeca pool (grafico): {dodeca_pool}")

    # === BUDGET MODE ===
    jackpot_for_mode = config["jackpot"]
    budget_mode = {
        "mode": "MINIMO", "emoji": "🟢", "n_sestinas": 1,
        "cost_eur": 1.0, "ev": 0.0,
        "message": "1 sestina."
    }
    if VORTEX_ENGINE_AVAILABLE:
        try:
            budget_mode = determine_budget_mode(jackpot_for_mode)
            print(f"[+] Budget mode: {budget_mode['emoji']} {budget_mode['mode']}")
        except Exception as e:
            print(f"[!] Errore budget mode: {e}")

    # === FORZA 1 SESTINA (tranne SKIP) ===
    if budget_mode.get("mode") == "SKIP":
        n_sestinas = 0
    else:
        n_sestinas = 1

    skip_mode = (n_sestinas == 0)

    # === CALCOLA next_concorso ===
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

    # === GENERAZIONE ===
    all_sestinas = []
    if skip_mode:
        print("[*] SKIP: nessuna sestina.")
    else:
        pool = list(range(1, 91))
        if VORTEX_ENGINE_AVAILABLE:
            try:
                vortex_sel = select_vortex_sestinas_multi(
                    pool, None, history,
                    n_sestinas=n_sestinas, seed=next_concorso
                )
                all_sestinas = [list(s[0]) for s in vortex_sel]
                print(f"[+] {len(all_sestinas)} sestina da pool 1-90 "
                      f"(seed={next_concorso})")
            except Exception as e:
                print(f"[!] Errore generazione: {e}")
        else:
            print("[!] VORTEX ENGINE non disponibile.")

    # === TRACK RECORD ===
    # FIX (2026-10-05): detect_wins DEVE girare PRIMA di update_with_result.
    win_info = None
    if TRACK_AVAILABLE and last_draw and last_draw.get("combinazione"):
        try:
            win_info = detect_wins(
                last_draw.get("concorso"),
                last_draw.get("combinazione")
            )
            if win_info:
                print(f"[!] VINCITA RILEVATA! Concorso {win_info['concorso']} "
                      f"-> {win_info['best_hits']} punti")

            update_with_result(
                last_draw.get("concorso"),
                last_draw.get("combinazione")
            )
        except Exception as e:
            print(f"[!] Errore track record: {e}")

    if TRACK_AVAILABLE and all_sestinas:
        try:
            record_predictions(next_concorso, all_sestinas,
                               budget_mode.get("mode", "NORMALE"))
        except Exception as e:
            print(f"[!] Errore track record (record): {e}")

    # === DATABASE ===
    payload = build_database_payload(
        history, dodeca_pool, all_sestinas, next_concorso, budget_mode, config
    )
    save_json(DATABASE_FILE, payload)

    # === GRAFICI ===
    generate_vortex_chart(all_sestinas, dodeca_pool)

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

    personal_block = "—"
    if PERSONAL_AVAILABLE:
        try:
            personal_stats = analyze_played()
            personal_block = format_personal_report(personal_stats)
        except Exception as e:
            print(f"[!] Errore personal stats: {e}")

    track_block = "—"
    if TRACK_AVAILABLE:
        try:
            track_stats = get_track_stats()
            track_block = format_track_report(track_stats)
        except Exception as e:
            print(f"[!] Errore track stats: {e}")

    # === REPORT ===
    jackpot_for_report = payload.get("next_contest", {}).get(
        "jackpot", DEFAULT_JACKPOT)
    vortex_data = payload.get("vortex", {})
    ev_data = vortex_data.get("ev", {})
    rollover_data = vortex_data.get("rollover", {})
    bt_data = vortex_data.get("backtest", {})

    ev_line = "—"
    if ev_data:
        ev_line = (f"{ev_data.get('ev_total', 0):+.4f} € · "
                   f"{ev_data.get('recommendation', '—')}")

    rollover_line = "—"
    if rollover_data:
        rollover_line = (f"{rollover_data.get('emoji', '')} "
                         f"{rollover_data.get('level', '—')}")

    bt_line = "—"
    if bt_data and bt_data.get("total", 0) > 0:
        bt_line = (f"{bt_data.get('hit_rate_3plus', 0)}% "
                   f"(baseline {bt_data.get('baseline_expected', 0)}%)")

    bm = payload.get("budget_mode", {})
    bm_emoji = bm.get("emoji", "🟡")
    bm_mode = bm.get("mode", "NORMALE")
    bm_n = bm.get("n_sestinas", len(all_sestinas))
    bm_cost = bm.get("cost_eur", 1.0)
    bm_msg = bm.get("message", "")

    sestinas_lines = []
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
        sestinas_lines.append(
            f"🎲 {sestina}\n"
            f"   Somma: {s_sum} · Z: {s_z:+0.2f}\n"
            f"   ✦ {s_sig}"
        )

    if skip_mode:
        sestinas_block = "🚫 SKIP MODE — Nessuna sestina."
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
        f"🔥 SESTINA:\n"
        f"{sestinas_block}\n\n"
        f"🌌 Venus Vortex — Cosmic Pattern Engine\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <a href='{ANALYTICS_URL}'>Analytics Dashboard</a>\n"
        f"🏠 <a href='{DASHBOARD_URL}'>Dashboard Principale</a>"
    )

    send_telegram_photo(CHART_FILE, "")
    send_telegram_report_smart(report_text)

    if heatmap_path and os.path.exists(heatmap_path):
        send_telegram_photo(heatmap_path,
                            "🔥 Vortex Heatmap")

    if dist_path and os.path.exists(dist_path):
        send_telegram_photo(dist_path,
                            "📊 Distribuzione — Somme, Decadi, Parità")

    links_msg = (
        "📊 <b>ANALYTICS DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 <a href='{ANALYTICS_URL}'>Statistiche Complete</a>\n\n"
        f"🏠 <a href='{DASHBOARD_URL}'>Dashboard Principale</a>"
    )
    send_telegram_message(links_msg)

    if win_info:
        win_msg = format_win_notification(win_info)
        if win_msg:
            send_telegram_message(win_msg)

    print("=== VENUS VORTEX — COMPLETATO ===")


if __name__ == "__main__":
    main()
