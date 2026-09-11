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
        return
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"): token = token[3:]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {"chat_id": TELEGRAM_CHAT_ID.strip(), "caption": caption_html, "parse_mode": "HTML"}
            requests.post(url, data=payload, files={"photo": photo}, timeout=25)
    except Exception:
        pass

# ==========================================
# 1. MOTORE DI ACQUISIZIONE ZENIT
# ==========================================
def validate_zenit_data(data):
    if not data: return False
    if "N/A" in [data.get('concorso'), data.get('jolly'), data.get('superstar'), data.get('jackpot')]: return False
    if not isinstance(data.get('sestina'), list) or len(data.get('sestina')) != 6: return False
    if str(data.get('jackpot', '')).strip() in ["€ 10", "€ 0", "€", ""]: return False
    return True

def fetch_titan_superenalotto():
    targets = [
        "https://www.estrazionedellotto.it/estrazioni-superenalotto",
        "https://www.superenalotto.net/estrazioni"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    for target in targets:
        urls_to_try = [
            f"https://api.codetabs.com/v1/proxy?quest={target}",
            f"https://api.allorigins.win/get?url={urllib.parse.quote(target)}",
            target
        ]
        
        for url in urls_to_try:
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code != 200: continue
                
                html = res.json().get("contents", "") if "allorigins" in url else res.text
                if not html or len(html) < 500: continue
                
                soup = BeautifulSoup(html, 'html.parser')
                text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()

                if "cloudflare" in text.lower(): continue

                result = {
                    "concorso": "N/A",
                    "data": datetime.now().strftime("%d/%m/%Y"),
                    "sestina": [],
                    "jolly": "N/A",
                    "superstar": "N/A",
                    "jackpot": "N/A"
                }

                conc_match = re.search(r'(?:Concorso|Estrazione)\s*(?:N\.|n\.|Numero)?\s*(\d{1,4})\s*(?:del|-|/)?\s*(\d{2}[\/\-]\d{2}[\/\-]\d{4})', text, re.I)
                if conc_match:
                    result["concorso"], result["data"] = conc_match.groups()

                jp_match = re.search(r'(?:Jackpot|Montepremi)[^\d]{1,15}([0-9]{1,3}(?:\.[0-9]{3})*(?:\,[0-9]{2})?)', text, re.I)
                if jp_match and jp_match.group(1) not in ["10", "0"]:
                    result["jackpot"] = f"€ {jp_match.group(1).strip()}"

                jolly_match = re.search(r'Jolly[^\d]{1,10}(\d{1,2})\b', text, re.I)
                if jolly_match and 1 <= int(jolly_match.group(1)) <= 90:
                    result["jolly"] = int(jolly_match.group(1))

                ss_match = re.search(r'SuperStar[^\d]{1,10}(\d{1,2})\b', text, re.I)
                if ss_match and 1 <= int(ss_match.group(1)) <= 90:
                    result["superstar"] = int(ss_match.group(1))

                for block in text.split("Concorso"):
                    nums = [int(n) for n in re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', block)]
                    if len(nums) >= 6:
                        valid_nums = list(dict.fromkeys(n for n in nums if 1 <= n <= 90))
                        if len(valid_nums) >= 6:
                            result["sestina"] = sorted(valid_nums[:6])
                            break

                if validate_zenit_data(result):
                    return result
                    
            except Exception:
                continue

    return None

# ==========================================
# 2-4. CORE ENGINE & TERMODINAMICA
# ==========================================
def calculate_aerodynamic_wear(history):
    wear_matrix = np.zeros(MAX_NUM)
    window_length = min(len(history), 100)
    for idx in range(window_length):
        draw = history[idx]
        impact_weight = np.exp(-0.03 * idx)
        for num in draw.get("sestina", []):
            if isinstance(num, int) and 1 <= num <= MAX_NUM: wear_matrix[num - 1] += impact_weight
    max_wear = np.max(wear_matrix)
    return wear_matrix / max_wear if max_wear > 0 else wear_matrix

def train_attention_ml(history):
    valid_history = [d for d in history if validate_zenit_data(d)]
    if len(valid_history) < 15: return np.ones(MAX_NUM) / MAX_NUM
        
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
    valid_history = [d for d in history if validate_zenit_data(d)]
    if len(valid_history) < 20: return np.ones(MAX_NUM)
    freq_matrix = np.zeros((len(valid_history[:50]), MAX_NUM))
    for i, draw in enumerate(valid_history[:50]):
        for n in draw.get("sestina", []): 
            if isinstance(n, int) and 1 <= n <= MAX_NUM: freq_matrix[i, n-1] = 1
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
    np.random.seed(int(time.time() * 1000000) % 4294967295)
    noise = np.random.gumbel(0, 0.15, size=(iterations, MAX_NUM))
    
    total_kinetic_energy = physical_energy + noise
    top_6_indices = np.argpartition(total_kinetic_energy, -6, axis=1)[:, -6:]
    unique, counts = np.unique(top_6_indices, return_counts=True)
    
    physics_scores = np.zeros(MAX_NUM)
    physics_scores[unique] = counts / iterations
    return physics_scores

# ==========================================
# 5. VALIDATORE STRUTTURALE RIGIDO & SOLUTORE
# ==========================================
def calculate_anti_crowd_ev(sestina):
    sestina = sorted(sestina)
    penalty = sum(1 for n in sestina if n <= 31) * 0.8
    if len(set([n % 10 for n in sestina])) <= 3: penalty += 1.5
    if 1 in [sestina[i+1] - sestina[i] for i in range(len(sestina)-1)]: penalty += 1.2
    return round(10.0 / (1.0 + penalty), 2)

def is_structurally_valid(sestina):
    """Filtro matematico e statistico multilivello."""
    s = sorted(sestina)
    somma = sum(s)
    
    # 1. Filtro Gaussiano sulla somma
    if not (210 <= somma <= 340):
        return False
        
    # 2. Bilanciamento Pari / Dispari (tra 2 e 4 pari)
    pari = sum(1 for n in s if n % 2 == 0)
    if pari < 2 or pari > 4:
        return False
        
    # 3. Bilanciamento Alti / Bassi (tra 2 e 4 numeri <= 45)
    bassi = sum(1 for n in s if n <= 45)
    if bassi < 2 or bassi > 4:
        return False
        
    # 4. Esclusione di 3 o più numeri consecutivi
    for i in range(len(s) - 2):
        if s[i+2] == s[i+1] + 1 == s[i] + 2:
            return False
            
    return True

def build_titan_matrix(physics_scores):
    # 1. Selezioniamo i 18 numeri con il punteggio fisico/ML più alto
    top_18_indices = np.argsort(physics_scores)[-18:]
    pool_18 = [int(i + 1) for i in top_18_indices]
    
    valid_sestine = []
    
    # 2. Raccogliamo TUTTE le combinazioni valide nel pool (18.564 combinazioni analizzate)
    for sestina in combinations(pool_18, 6):
        if is_structurally_valid(sestina):
            s_sum = sum(sestina)
            ev = calculate_anti_crowd_ev(sestina)
            valid_sestine.append({
                "sestina": sorted(sestina),
                "somma": s_sum,
                "ev_index": ev
            })
                
    # 3. Fallback di sicurezza senza duplicati se il pool genera meno di 4 sestine valide
    if len(valid_sestine) < 4:
        fallback_pool = list(range(1, 91))
        while len(valid_sestine) < 4:
            s = sorted(np.random.choice(fallback_pool, 6, replace=False))
            if is_structurally_valid(s):
                if not any(x["sestina"] == s for x in valid_sestine):
                    valid_sestine.append({
                        "sestina": s,
                        "somma": sum(s),
                        "ev_index": calculate_anti_crowd_ev(s)
                    })
                
    # 4. Ordiniamo TUTTE le valide per EV decrescente e prendiamo le top 4 in assoluto
    valid_sestine.sort(key=lambda x: x["ev_index"], reverse=True)
    top_4 = valid_sestine[:4]
    
    # 5. Dodecaedro effettivo: ricaviamo i 12 numeri unici realmente usati nelle 4 sestine vincenti
    dodecaedro = sorted(list(set([num for item in top_4 for num in item["sestina"]])))
    
    # Se le 4 sestine usano meno di 12 numeri unici, completiamo a 12 usando i migliori dal pool_18
    if len(dodecaedro) < 12:
        extra = [n for n in reversed(pool_18) if n not in dodecaedro]
        dodecaedro = sorted((dodecaedro + extra)[:12])
    else:
        dodecaedro = dodecaedro[:12]

    matrix = [{"id": f"TITAN {i}", **item} for i, item in enumerate(top_4, 1)]
    
    return dodecaedro, matrix

# ==========================================
# 6. GRAFICA E DASHBOARD
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
    ax1.set_title(f'Field Area (Somma Ultima Estrazione: {somma})')
    
    scores = [physics_scores[n-1] for n in pool_12]
    ax2.barh([f"N°{n}" for n in pool_12], scores, color='#3b82f6')
    ax2.set_title('Termodinamica Pool 12')
    ax2.invert_yaxis()
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

def generate_web_dashboard(se_data, pool_12, matrix):
    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')

    html = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITAN GOD MODE</title><style>body {{ background: #09090b; color: #f8fafc; font-family: sans-serif; padding: 2rem; }} .container {{ max-width: 900px; margin: 0 auto; background: #18181b; padding: 2rem; border-radius: 12px; }} h1 {{ color: #a855f7; text-align: center; }} .data-box {{ display: flex; justify-content: space-between; background: #27272a; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }} .data-item strong {{ font-size: 1.5rem; color: #34d399; }} .pool {{ background: #27272a; padding: 1rem; border-radius: 8px; text-align: center; font-size: 1.2rem; color: #a855f7; margin-bottom: 2rem; border: 1px dashed #a855f7; }} .card {{ background: #09090b; border-left: 5px solid #3b82f6; padding: 1.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }} .nums {{ font-size: 1.4rem; font-weight: bold; }}</style></head><body><div class="container"><h1>TITAN God Mode Optimal</h1><div class="data-box"><div class="data-item">Concorso<br><strong>N° {conc}</strong></div><div class="data-item">Data<br><strong>{data_est}</strong></div><div class="data-item">Jackpot<br><strong>{jackpot}</strong></div></div><h3 style="color: #a1a1aa;">Ultima Estrazione</h3><div class="pool" style="color: #34d399;">{sestina} | Jolly: {jolly} | SuperStar: {superstar}</div><h3 style="color: #a1a1aa;">Dodecaedro A.I.</h3><div class="pool">{pool_12}</div><h3 style="color: #a1a1aa;">Matrice Ottimizzata</h3>"""
    for m in matrix: html += f"""<div class="card"><div><div style="color: #3b82f6; font-size: 0.8rem;">{m['id']}</div><div class="nums">{m['sestina']}</div></div><div style="text-align: right; color: #a1a1aa;">Somma: {m['somma']}<br>EV Score: <strong style="color: #fbbf24;">{m['ev_index']} ⚡</strong></div></div>"""
    html += "</div></body></html>"
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f: f.write(html)

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    history = []
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: raw_history = json.load(f)
            history = [h for h in raw_history if validate_zenit_data(h)]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history, f, indent=2)
        except Exception:
            history = []

    se_data = fetch_titan_superenalotto()
    
    if not se_data:
        if len(history) > 0:
            se_data = history[0]
        else:
            print("Errore critico: Impossibile recuperare dati e nessun storico valido.")
            sys.exit(1)
            
    if validate_zenit_data(se_data):
        if not any(str(i.get("concorso")) == str(se_data.get("concorso")) for i in history):
            history.insert(0, se_data)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history, f, indent=2)

    # PIPELINE ESTRATTIVA CON FILTRI GAUSSIANI
    anomalies = detect_venus_anomalies(history)
    ml_probs = train_attention_ml(history)
    physics_scores = simulate_1M_venus(history, ml_probs, anomalies)
    pool_12, matrix = build_titan_matrix(physics_scores)
    
    generate_titan_chart(se_data.get("sestina", []), pool_12, physics_scores)
    generate_web_dashboard(se_data, pool_12, matrix)

    # TELEGRAM NOTIFY
    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')

    pred_text = "".join([f"🔹 <b>{m['id']}:</b> <code>{m['sestina']}</code>\n   ↳ 📊 Somma: <b>{m['somma']}</b> | ⚡ Anti-Massa: <b>{m['ev_index']}</b>\n" for m in matrix])
    caption = (
        f"👑 <b>TITAN — OPTIMAL MATRIX</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Estrazione:</b> N° {conc} ({data_est})\n"
        f"🎲 <b>Venus:</b> <code>{sestina}</code>\n"
        f"🎯 <b>Jolly:</b> {jolly} | ⭐ <b>SuperStar:</b> {superstar}\n"
        f"💰 <b>Jackpot:</b> <b>{jackpot}</b>\n\n"
        f"🧬 <b>DODECAEDRO A.I. (BILANCIATO):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>SISTEMA TITAN (SOMME 210-340):</b>\n{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🌐 Sincronizzazione completata su GitHub Pages.</i>"
    )
    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
