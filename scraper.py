import os
import re
import json
import sys
import time
import urllib.parse
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
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM WARN] Token o Chat ID non configurati.")
        return
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"): token = token[3:]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {"chat_id": TELEGRAM_CHAT_ID.strip(), "caption": caption_html, "parse_mode": "HTML"}
            res = requests.post(url, data=payload, files={"photo": photo}, timeout=25)
            print(f"[TELEGRAM LOG] Status: {res.status_code}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# ==========================================
# 1. TITAN SCRAPER SPATIAL DOM PARSER
# ==========================================
def fetch_titan_superenalotto():
    timestamp = int(time.time())
    
    # Pool di target ridondanti
    urls = [
        "https://www.superenalotto.com/estrazioni",
        "https://www.superenalotto.net/estrazioni",
        "https://www.estrazionedellotto.it/estrazioni-superenalotto"
    ]

    for base_url in urls:
        try:
            proxy_url = f"https://api.allorigins.win/get?url={urllib.parse.quote(base_url + '?t=' + str(timestamp))}"
            print(f"[INFO] Scansione target: {base_url} via AllOrigins...")
            res = requests.get(proxy_url, timeout=20)
            if res.status_code != 200: continue
            
            html = res.json().get("contents", "")
            if not html: continue
            
            soup = BeautifulSoup(html, 'html.parser')
            text_clean = re.sub(r'\s+', ' ', soup.get_text(separator=' '))
            
            result = {
                "concorso": "N/A",
                "data": datetime.now().strftime("%d/%m/%Y"),
                "sestina": [],
                "jolly": "N/A",
                "superstar": "N/A",
                "jackpot": "N/A"
            }

            # A. ESTRAZIONE JACKPOT
            jp_m = re.search(r'(?:Jackpot|Montepremi)[^\d]*([0-9]{1,3}(?:\.[0-9]{3})*(?:\,[0-9]{2})?)', text_clean, re.I)
            if jp_m: result["jackpot"] = f"€ {jp_m.group(1).strip()}"

            # B. ESTRAZIONE CONCORSO E DATA
            conc_m = re.search(r'(?:Concorso|Estrazione)\s*(?:N\.|Numero)?\s*(\d{1,4})\s*(?:del|-|/)?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})', text_clean, re.I)
            if conc_m:
                result["concorso"] = conc_m.group(1)
                result["data"] = conc_m.group(2)

            # C. ESTRAZIONE JOLLY E SUPERSTAR TRAMITE ADIACENZA TESTUALE
            jolly_m = re.search(r'Jolly[^\d]*(\d{1,2})\b', text_clean, re.I)
            if jolly_m and 1 <= int(jolly_m.group(1)) <= 90: result["jolly"] = int(jolly_m.group(1))
            
            ss_m = re.search(r'SuperStar[^\d]*(\d{1,2})\b', text_clean, re.I)
            if ss_m and 1 <= int(ss_m.group(1)) <= 90: result["superstar"] = int(ss_m.group(1))

            # D. ESTRAZIONE SESTINA (DOM NODE ISOLATION)
            for container in soup.find_all(['ul', 'div', 'tr', 'p']):
                classes = ' '.join(container.get('class', [])).lower()
                # Cerca nodi con CSS class espliciti
                if any(k in classes for k in ['ball', 'numer', 'vincent', 'estraz', 'lotto', 'palla', 'jolly', 'super']):
                    nums = [int(n) for n in re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', container.get_text(separator=' '))]
                    seen = set()
                    nums_unique = [x for x in nums if not (x in seen or seen.add(x))]
                    
                    if 6 <= len(nums_unique) <= 8:
                        result["sestina"] = sorted(nums_unique[:6])
                        # Auto-assegnazione posizionale se i label di testo falliscono
                        if len(nums_unique) >= 7 and result["jolly"] == "N/A": result["jolly"] = nums_unique[6]
                        if len(nums_unique) == 8 and result["superstar"] == "N/A": result["superstar"] = nums_unique[7]
                        break

            # E. FALLBACK EXTREME (Window Sliding Logic)
            if not result["sestina"]:
                all_nums = [int(n) for n in re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', text_clean)]
                for i in range(len(all_nums) - 5):
                    window = all_nums[i:i+6]
                    if len(set(window)) == 6:
                        result["sestina"] = sorted(window)
                        if i + 6 < len(all_nums) and result["jolly"] == "N/A": result["jolly"] = all_nums[i+6]
                        if i + 7 < len(all_nums) and result["superstar"] == "N/A": result["superstar"] = all_nums[i+7]
                        break

            if len(result["sestina"]) == 6:
                print(f"[SUCCESS] Dati perfetti estratti da {base_url}")
                return result
                
        except Exception as e:
            print(f"[WARN] Fallimento spaziale su {base_url}: {e}")
            continue

    print("[ERROR] Tutti i proxy falliti. Impossibile acquisire dati in tempo reale.")
    return None

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
            if isinstance(num, int) and 1 <= num <= MAX_NUM:
                wear_matrix[num - 1] += impact_weight
    max_wear = np.max(wear_matrix)
    return wear_matrix / max_wear if max_wear > 0 else wear_matrix

def train_attention_ml(history):
    valid_history = [d for d in history if d.get("sestina") and len(d.get("sestina", [])) == 6]
    if len(valid_history) < 15: 
        return np.ones(MAX_NUM) / MAX_NUM
        
    X, y = [], []
    for i in range(len(valid_history) - 1, 4, -1):
        window = valid_history[i-4:i]
        X.append([1 if n in [num for d in window for num in d.get("sestina", [])] else 0 for n in range(1, MAX_NUM + 1)])
        y.append([1 if n in valid_history[i-5].get("sestina", []) else 0 for n in range(1, MAX_NUM + 1)])

    model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
    model.fit(np.array(X), np.array(y))
    
    curr_window = [1 if n in [num for d in valid_history[:4] for num in d.get("sestina", [])] else 0 for n in range(1, MAX_NUM + 1)]
    return np.array([p[0][1] if len(p[0]) > 1 else 0.01 for p in model.predict_proba([curr_window])])

def detect_venus_anomalies(history):
    valid_history = [d for d in history if d.get("sestina") and len(d.get("sestina", [])) == 6]
    if len(valid_history) < 20: 
        return np.ones(MAX_NUM)
        
    freq_matrix = np.zeros((len(valid_history[:50]), MAX_NUM))
    for i, draw in enumerate(valid_history[:50]):
        for n in draw.get("sestina", []): 
            if isinstance(n, int) and 1 <= n <= MAX_NUM:
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
    somma = sum(sestina) if sestina else 273
    x = np.linspace(100, 450, 500)
    y = stats.norm.pdf(x, 273.0, 45.5)
    ax1.plot(x, y, color='#d946ef', linewidth=2.5)
    ax1.fill_between(x, y, color='#d946ef', alpha=0.15)
    ax1.axvline(somma, color='#14b8a6', linestyle='--', linewidth=2)
    ax1.set_title(f'Field Area (Somma: {somma})')

    scores = [physics_scores[n-1] for n in pool_12]
    ax2.barh([f"N°{n}" for n in pool_12], scores, color='#3b82f6')
    ax2.set_title('Termodinamica ILP (1M Iter)')
    ax2.invert_yaxis()

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

# ==========================================
# 8. DASHBOARD HTML 
# ==========================================
def generate_web_dashboard(se_data, pool_12, matrix):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="it">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TITAN GOD MODE - Dashboard</title>
        <style>
            body {{ background-color: #09090b; color: #f8fafc; font-family: sans-serif; padding: 2rem; margin: 0; }}
            .container {{ max-width: 900px; margin: 0 auto; background: #18181b; padding: 2rem; border-radius: 12px; border: 1px solid #27272a; }}
            h1 {{ color: #a855f7; text-align: center; text-transform: uppercase; }}
            .data-box {{ display: flex; justify-content: space-between; background: #27272a; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }}
            .data-item {{ text-align: center; }}
            .data-item strong {{ font-size: 1.5rem; color: #34d399; }}
            .sestina-card {{ background: #09090b; border: 1px solid #3f3f46; border-left: 5px solid #3b82f6; padding: 1.5rem; margin-bottom: 1rem; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; }}
            .nums {{ font-size: 1.4rem; font-weight: bold; color: #f8fafc; }}
            .pool {{ background: #27272a; padding: 1rem; border-radius: 8px; text-align: center; font-size: 1.2rem; color: #a855f7; margin-bottom: 2rem; border: 1px dashed #a855f7; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>TITAN God Mode V2</h1>
            <div class="data-box">
                <div class="data-item"><span>Concorso</span><br><strong>N° {se_data.get('concorso', 'N/A')}</strong></div>
                <div class="data-item"><span>Data</span><br><strong>{se_data.get('data', 'N/A')}</strong></div>
                <div class="data-item"><span>Jackpot</span><br><strong>{se_data.get('jackpot', 'N/A')}</strong></div>
            </div>
            
            <h3 style="color: #a1a1aa;">Ultima Estrazione Venus</h3>
            <div class="pool" style="color: #34d399;">
                {se_data.get('sestina', [])} &nbsp;|&nbsp; Jolly: {se_data.get('jolly', 'N/A')} &nbsp;|&nbsp; SuperStar: {se_data.get('superstar', 'N/A')}
            </div>

            <h3 style="color: #a1a1aa;">Dodecaedro Quantistico (12 Numeri)</h3>
            <div class="pool">{pool_12}</div>

            <h3 style="color: #a1a1aa;">Matrice Ottimizzata (Max EV)</h3>
    """
    for m in matrix:
        html_content += f"""
            <div class="sestina-card">
                <div>
                    <div style="font-size: 0.8rem; color: #3b82f6;">{m['id']}</div>
                    <div class="nums">{m['sestina']}</div>
                </div>
                <div style="text-align: right; color: #a1a1aa;">
                    Somma: {m['somma']}<br>
                    EV Score: <strong style="color: #fbbf24;">{m['ev_index']} ⚡</strong>
                </div>
            </div>
        """
    html_content += "</div></body></html>"
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

# ==========================================
# MAIN EXECUTION & DB HEALING
# ==========================================
def main():
    print("⚡ INITIALIZING TITAN ENGINE... ⚡")
    
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: 
                raw_history = json.load(f)
                
            # PULIZIA DB: Elimina i record corrotti generati dai run falliti in precedenza
            for h in raw_history:
                if h.get("concorso") not in [None, "0", "N/A"] and len(h.get("sestina", [])) == 6 and h.get("jolly") != "N/A":
                    history.append(h)
                    
            # Sovrascrive istantaneamente il DB guarendolo
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
                
        except Exception:
            history = []

    # Esegue il nuovo Scraper
    se_data = fetch_titan_superenalotto()
    
    if not se_data:
        if len(history) > 0:
            print(f"[FALLBACK] Uso dati puliti del concorso {history[0].get('concorso', 'N/A')}")
            se_data = history[0]
        else:
            print("[ERROR] Nessun dato online e storico vuoto/corrotto. Impossibile procedere.")
            sys.exit(1)
    else:
        if not any(str(i.get("concorso")) == str(se_data["concorso"]) for i in history):
            history.insert(0, se_data)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: 
                json.dump(history, f, indent=2)

    # TITAN CORE PIPELINE
    anomalies = detect_venus_anomalies(history)
    ml_probs = train_attention_ml(history)
    physics_scores = simulate_1M_venus(history, ml_probs, anomalies)
    pool_12, matrix = build_titan_matrix(physics_scores)
    
    generate_titan_chart(se_data.get("sestina", []), pool_12, physics_scores)
    generate_web_dashboard(se_data, pool_12, matrix)

    pred_text = "".join([f"🔹 <b>{m['id']}:</b> <code>{m['sestina']}</code>\n   ↳ 📊 Somma: <b>{m['somma']}</b> | ⚡ Anti-Massa: <b>{m['ev_index']}</b>\n" for m in matrix])
    caption = (
        f"👑 <b>TITAN — GOD MODE V2 SEALED</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Estrazione:</b> N° {se_data.get('concorso', 'N/A')} ({se_data.get('data', 'N/A')})\n"
        f"🎲 <b>Venus:</b> <code>{se_data.get('sestina', [])}</code>\n"
        f"🎯 <b>Jolly:</b> {se_data.get('jolly', 'N/A')} | ⭐ <b>SuperStar:</b> {se_data.get('superstar', 'N/A')}\n"
        f"💰 <b>Jackpot:</b> <b>{se_data.get('jackpot', 'N/A')}</b>\n\n"
        f"🧬 <b>DODECAEDRO A.I. (ILP SOLVER):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>SISTEMA ANTI-FOLLA TITAN:</b>\n{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🌐 Dashboard aggiornata su GitHub Pages.</i>"
    )
    
    print("[INFO] Invio notifica su Telegram...")
    send_telegram_photo(CHART_FILE, caption)
    print("✅ ESECUZIONE COMPLETATA CON SUCCESSO.")

if __name__ == "__main__":
    main()
