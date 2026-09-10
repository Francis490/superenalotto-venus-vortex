import os
import re
import json
import sys
import time
import requests
import numpy as np
import scipy.stats as stats
from scipy.optimize import milp, LinearConstraint, Bounds
from itertools import combinations
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier, IsolationForest

# ==========================================
# CONFIGURAZIONE E VARIABILI GLOBALI
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "venus_history.json"
DASHBOARD_FILE = "index.html"
CHART_FILE = "vortex_chart.png"
MAX_NUM = 90

# ==========================================
# 0. TELEGRAM NOTIFIER ENGINE
# ==========================================
def send_telegram_photo(photo_path, caption_html):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"): token = token[3:]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {"chat_id": TELEGRAM_CHAT_ID.strip(), "caption": caption_html, "parse_mode": "HTML"}
            requests.post(url, data=payload, files={"photo": photo}, timeout=25)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# ==========================================
# 1. SCRAPER AVANZATO CON ANTI-CACHE & API SISAL
# ==========================================
def fetch_superenalotto():
    timestamp = int(time.time())
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

    # Tentativo 1: API JSON Diretta Sisal
    try:
        sisal_api = f"https://www.sisal.it/api/site-lotteries/drawings/superenalotto/latest?_={timestamp}"
        res = requests.get(sisal_api, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            drawing = data.get("drawing", data)
            conc_num = drawing.get("number") or drawing.get("concorso")
            sestina = drawing.get("extractedNumbers") or drawing.get("sestina")
            
            if conc_num and sestina and len(sestina) >= 6:
                jolly = drawing.get("jollyNumber", "N/A")
                superstar = drawing.get("superStarNumber", "N/A")
                date_str = drawing.get("date", datetime.now().strftime("%d/%m/%Y"))
                jackpot_val = f"€ {drawing.get('jackpot', '222.400.000')}"
                
                print(f"[SUCCESS] Dati letti da API Sisal. Concorso {conc_num}")
                return {
                    "concorso": str(conc_num),
                    "data": date_str,
                    "sestina": sorted([int(x) for x in sestina[:6]]),
                    "jolly": int(jolly) if str(jolly).isdigit() else "N/A",
                    "superstar": int(superstar) if str(superstar).isdigit() else "N/A",
                    "jackpot": jackpot_val
                }
    except Exception as e:
        print(f"[WARN] API Sisal non raggiungibile ({e}). Passaggio a Web Scraping.")

    # Tentativo 2: Scraping HTML con Cache-Busting
    urls = [
        f"https://www.superenalotto.net/estrazioni?t={timestamp}",
        f"https://www.estrazionedellotto.it/estrazioni-superenalotto?t={timestamp}"
    ]

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                text = soup.get_text()

                jackpot_val = "€ 222.400.000"
                jp_match = re.search(r'(?:jackpot|montepremi)[:\s]*€?\s*([\d\.\,]+\s*(?:milioni|mila)?)', text, re.I)
                if jp_match: jackpot_val = f"€ {jp_match.group(1).strip()}"

                # Estrazione palline
                balls = soup.select('.ball, .numero, ul.balls li, span.ball, div.ball, td.ball')
                extracted = []
                for b in balls:
                    val = b.text.strip()
                    if val.isdigit() and 1 <= int(val) <= 90:
                        if int(val) not in extracted: extracted.append(int(val))

                if len(extracted) >= 6:
                    date_m = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                    conc_m = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text, re.I)
                    
                    if conc_m:
                        conc_num = conc_m.group(1)
                        print(f"[SUCCESS] Dati letti da Web Scraper ({url}). Concorso {conc_num}")
                        return {
                            "concorso": str(conc_num),
                            "data": date_m.group(1) if date_m else datetime.now().strftime("%d/%m/%Y"),
                            "sestina": sorted(extracted[:6]),
                            "jolly": extracted[6] if len(extracted) > 6 else "N/A",
                            "superstar": extracted[7] if len(extracted) > 7 else "N/A",
                            "jackpot": jackpot_val
                        }
        except Exception:
            continue

    print("[WARN] Rete bloccata o sorgenti non aggiornate. Fallback su locale.")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            hist = json.load(f)
            if hist: return hist[0]

    return {"concorso": "0", "data": datetime.now().strftime("%d/%m/%Y"), "sestina": [], "jolly": "N/A", "superstar": "N/A", "jackpot": "N/A"}

# ==========================================
# 2-4. CORE ENGINE (ML, ANOMALY, TERMODINAMICA)
# ==========================================
def calculate_aerodynamic_wear(history):
    wear_matrix = np.zeros(MAX_NUM)
    window_length = min(len(history), 100)
    
    for idx in range(window_length):
        draw = history[idx]
        impact_weight = np.exp(-0.03 * idx)
        for num in draw.get("sestina", []):
            if 1 <= num <= MAX_NUM:
                wear_matrix[num - 1] += impact_weight
                
    max_wear = np.max(wear_matrix)
    return wear_matrix / max_wear if max_wear > 0 else wear_matrix

def train_attention_ml(history):
    if len(history) < 15: 
        return np.ones(MAX_NUM) / MAX_NUM
        
    X, y = [], []
    for i in range(len(history) - 1, 4, -1):
        window = history[i-4:i]
        X.append([1 if n in [num for d in window for num in d.get("sestina", [])] else 0 for n in range(1, MAX_NUM + 1)])
        y.append([1 if n in history[i-5].get("sestina", []) else 0 for n in range(1, MAX_NUM + 1)])

    model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
    model.fit(np.array(X), np.array(y))
    
    curr_window = [1 if n in [num for d in history[:4] for num in d.get("sestina", [])] else 0 for n in range(1, MAX_NUM + 1)]
    return np.array([p[0][1] if len(p[0]) > 1 else 0.01 for p in model.predict_proba([curr_window])])

def detect_venus_anomalies(history):
    if len(history) < 20: 
        return np.ones(MAX_NUM)
        
    freq_matrix = np.zeros((len(history[:50]), MAX_NUM))
    for i, draw in enumerate(history[:50]):
        for n in draw.get("sestina", []): 
            if 1 <= n <= MAX_NUM:
                freq_matrix[i, n-1] = 1
                
    anomalies = IsolationForest(contamination=0.1, random_state=42).fit_predict(freq_matrix.T)
    return np.where(anomalies == -1, 1.5, 1.0)

def simulate_1M_venus(history, ml_probs, anomaly_scores, iterations=1000000):
    delays = np.full(MAX_NUM, len(history))
    for num in range(1, MAX_NUM + 1):
        for i, draw in enumerate(history):
            if num in draw.get("sestina", []):
                delays[num-1] = i
                break

    aero_wear = calculate_aerodynamic_wear(history)
    base_energy = (np.log1p(delays) * 0.15) + (ml_probs * 2.5) + (anomaly_scores * 0.5)
    physical_energy = base_energy * (1.0 + (aero_wear * 0.20))

    noise_factor = 0.15
    np.random.seed(int(time.time() * 1000000) % 4294967295)
    noise = np.random.gumbel(0, noise_factor, size=(iterations, MAX_NUM))
    
    total_kinetic_energy = physical_energy + noise
    top_6_indices = np.argpartition(total_kinetic_energy, -6, axis=1)[:, -6:]
    unique, counts = np.unique(top_6_indices, return_counts=True)
    
    physics_scores = np.zeros(MAX_NUM)
    physics_scores[unique] = counts / iterations
    return physics_scores

# ==========================================
# 5. SOLUTORE ILP & TEORIA DEI GIOCHI
# ==========================================
def calculate_anti_crowd_ev(sestina):
    sestina = sorted(sestina)
    penalty = sum(1 for n in sestina if n <= 31) * 0.8
    if len(set([n % 10 for n in sestina])) <= 3: penalty += 1.5
    if 1 in [sestina[i+1] - sestina[i] for i in range(len(sestina)-1)]: penalty += 1.2
    return round(10.0 / (1.0 + penalty), 2)

def ilp_optimal_coverage(pool_12, num_sestine=4):
    all_sestine = list(combinations(pool_12, 6))
    all_triplets = list(combinations(pool_12, 3))
    
    trip_map = {t: i for i, t in enumerate(all_triplets)}
    A = np.zeros((len(all_triplets), len(all_sestine)))
    for j, sestina in enumerate(all_sestine):
        for trip in combinations(sestina, 3): A[trip_map[trip], j] = 1

    try:
        res = milp(c=-np.sum(A, axis=0), integrality=np.ones(len(all_sestine)), 
                   constraints=LinearConstraint(np.ones((1, len(all_sestine))), [num_sestine], [num_sestine]), 
                   bounds=Bounds(0, 1))
        if res.success: return [list(all_sestine[i]) for i in np.where(res.x > 0.5)[0]][:num_sestine]
    except Exception: pass
    
    return [list(all_sestine[0]), list(all_sestine[-1]), list(all_sestine[len(all_sestine)//2]), list(all_sestine[len(all_sestine)//3])][:num_sestine]

def build_titan_matrix(physics_scores):
    pool_12 = sorted([int(i + 1) for i in np.argsort(physics_scores)[-12:]])
    matrix_output = []
    
    for i, s in enumerate(ilp_optimal_coverage(pool_12, 4), 1):
        matrix_output.append({
            "id": f"TITAN {i}",
            "sestina": sorted(s),
            "somma": sum(s),
            "ev_index": calculate_anti_crowd_ev(s)
        })
    matrix_output.sort(key=lambda x: x["ev_index"], reverse=True)
    return pool_12, matrix_output

# ==========================================
# 6. GRAFICA TITAN
# ==========================================
def generate_titan_chart(sestina, pool_12, physics_scores):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), facecolor='#050505')
    somma = sum(sestina)
    x = np.linspace(100, 450, 500)
    y = stats.norm.pdf(x, 273.0, 45.5)
    ax1.plot(x, y, color='#d946ef', linewidth=2.5)
    ax1.fill_between(x, y, color='#d946ef', alpha=0.15)
    ax1.axvline(somma, color='#14b8a6', linestyle='--', linewidth=2)
    ax1.set_title(f'Conformal Uncertainty Field (Somma: {somma})')

    scores = [physics_scores[n-1] for n in pool_12]
    ax2.barh([f"N°{n}" for n in pool_12], scores, color='#3b82f6')
    ax2.set_title('Termodinamica ILP (1M Iter)')
    ax2.invert_yaxis()

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

# ==========================================
# 8. LIVELLO WEB: GENERAZIONE DASHBOARD HTML
# ==========================================
def generate_web_dashboard(se_data, pool_12, matrix):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TITAN GOD MODE - Live Dashboard</title>
        <style>
            body {{ background-color: #09090b; color: #f8fafc; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 2rem; margin: 0; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #18181b; padding: 2rem; border-radius: 12px; border: 1px solid #27272a; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
            h1 {{ color: #a855f7; text-align: center; text-transform: uppercase; letter-spacing: 2px; }}
            .data-box {{ display: flex; justify-content: space-between; background: #27272a; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }}
            .data-item {{ text-align: center; }}
            .data-item span {{ display: block; font-size: 0.9rem; color: #a1a1aa; margin-bottom: 0.5rem; text-transform: uppercase; }}
            .data-item strong {{ font-size: 1.5rem; color: #34d399; }}
            .sestina-card {{ background: #09090b; border: 1px solid #3f3f46; border-left: 5px solid #3b82f6; padding: 1.5rem; margin-bottom: 1rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }}
            .nums {{ font-size: 1.4rem; font-weight: bold; letter-spacing: 3px; color: #f8fafc; }}
            .stats {{ font-size: 0.9rem; color: #a1a1aa; text-align: right; }}
            .ev-score {{ color: #fbbf24; font-weight: bold; font-size: 1.1rem; }}
            .pool {{ background: #27272a; padding: 1rem; border-radius: 8px; text-align: center; font-size: 1.2rem; letter-spacing: 2px; color: #a855f7; margin-bottom: 2rem; border: 1px dashed #a855f7; }}
            .footer {{ text-align: center; margin-top: 2rem; font-size: 0.8rem; color: #52525b; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>TITAN God Mode V2</h1>
            <div class="data-box">
                <div class="data-item"><span>Concorso</span><strong>N° {se_data['concorso']}</strong></div>
                <div class="data-item"><span>Data</span><strong>{se_data['data']}</strong></div>
                <div class="data-item"><span>Jackpot</span><strong>{se_data['jackpot']}</strong></div>
            </div>
            
            <h3 style="color: #a1a1aa; border-bottom: 1px solid #3f3f46; padding-bottom: 0.5rem;">Ultima Estrazione Venus</h3>
            <div class="pool" style="color: #34d399; border-color: #34d399;">
                {se_data['sestina']} &nbsp;|&nbsp; <span style="color: #fbbf24;">J: {se_data['jolly']}</span> &nbsp;|&nbsp; <span style="color: #f87171;">SS: {se_data['superstar']}</span>
            </div>

            <h3 style="color: #a1a1aa; border-bottom: 1px solid #3f3f46; padding-bottom: 0.5rem;">Dodecaedro Quantistico (12 Numeri)</h3>
            <div class="pool">{pool_12}</div>

            <h3 style="color: #a1a1aa; border-bottom: 1px solid #3f3f46; padding-bottom: 0.5rem;">Matrice Ottimizzata (Max EV)</h3>
    """
    for m in matrix:
        html_content += f"""
            <div class="sestina-card">
                <div>
                    <div style="font-size: 0.8rem; color: #3b82f6; margin-bottom: 5px;">{m['id']}</div>
                    <div class="nums">{m['sestina']}</div>
                </div>
                <div class="stats">
                    Somma: {m['somma']}<br>
                    Anti-Massa Score: <span class="ev-score">{m['ev_index']} ⚡</span>
                </div>
            </div>
        """
    
    html_content += f"""
            <div class="footer">Ultimo Aggiornamento: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")} | Vettorizzazione: 1M Iterazioni | Solver: SciPy MILP</div>
        </div>
    </body>
    </html>
    """
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

# ==========================================
# MAIN EXECUTION (GOD MODE)
# ==========================================
def main():
    print("⚡ INITIALIZING TITAN / GOD MODE V2... ⚡")
    se_data = fetch_superenalotto()
    
    if not se_data or se_data.get("concorso") == "0":
        print("[ERROR] Impossibile recuperare i dati dell'estrazione. Abort execution.")
        sys.exit(1)
        
    history = []
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: history = json.load(f)

    if any(str(i.get("concorso")) == str(se_data["concorso"]) for i in history):
        print(f"[INFO] Concorso {se_data['concorso']} già elaborato. Halt.")
        sys.exit(0)

    history.insert(0, se_data)
    with open(HISTORY_FILE, "w") as f: json.dump(history, f, indent=2)

    # TITAN CORE PIPELINE
    anomalies = detect_venus_anomalies(history)
    ml_probs = train_attention_ml(history)
    physics_scores = simulate_1M_venus(history, ml_probs, anomalies)
    pool_12, matrix = build_titan_matrix(physics_scores)
    
    generate_titan_chart(se_data["sestina"], pool_12, physics_scores)
    generate_web_dashboard(se_data, pool_12, matrix)

    # Telegram Output
    pred_text = "".join([f"🔹 <b>{m['id']}:</b> <code>{m['sestina']}</code>\n   ↳ 📊 Somma: <b>{m['somma']}</b> | ⚡ Anti-Massa Score: <b>{m['ev_index']}</b>\n" for m in matrix])
    
    caption = (
        f"👑 <b>TITAN — GOD MODE V2 SEALED</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Estrazione:</b> N° {se_data['concorso']} ({se_data['data']})\n"
        f"🎲 <b>Venus:</b> <code>{se_data['sestina']}</code>\n"
        f"🎯 <b>Jolly:</b> {se_data['jolly']} | ⭐ <b>SuperStar:</b> {se_data['superstar']}\n"
        f"💰 <b>Jackpot:</b> <b>{se_data['jackpot']}</b>\n\n"
        f"🧬 <b>DODECAEDRO A.I. (ILP SOLVER):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>SISTEMA ANTI-FOLLA TITAN:</b>\n{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🌐 Live Dashboard aggiornata su GitHub Pages.</i>"
    )
    
    send_telegram_photo(CHART_FILE, caption)
    print("✅ TITAN GOD MODE EXECUTED PERFECTLY.")

if __name__ == "__main__":
    main()
