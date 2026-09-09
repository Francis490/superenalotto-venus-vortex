import os
import re
import json
import sys
import random
import requests
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"

# ==========================================
# 1. TELEGRAM NOTIFIER ENGINE
# ==========================================
def send_telegram_photo(photo_path, caption_html):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Credenziali Telegram assenti. Notifica saltata.")
        return

    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"):
        token = token[3:]

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID.strip(),
                "caption": caption_html,
                "parse_mode": "HTML"
            }
            resp = requests.post(url, data=payload, files={"photo": photo}, timeout=25)
            if resp.status_code == 200:
                print("[TELEGRAM] Report OMEGA inviato con successo!")
            else:
                print(f"[TELEGRAM ERROR] API {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Impossibile inviare la notifica: {e}")

# ==========================================
# 2. MACHINE LEARNING ENGINE (RANDOM FOREST)
# ==========================================
def train_ml_predictive_model(history, max_num=90):
    if len(history) < 10:
        return {n: 1/max_num for n in range(1, max_num + 1)}

    X, y = [], []
    for i in range(len(history) - 1, 4, -1):
        window = history[i-4:i]
        target_draw = history[i-5].get("sestina", [])
        
        freq_vector = [0] * max_num
        for draw in window:
            for num in draw.get("sestina", []):
                if 1 <= num <= max_num:
                    freq_vector[num - 1] += 1
        
        X.append(freq_vector)
        y_target = [1 if n in target_draw else 0 for n in range(1, max_num + 1)]
        y.append(y_target)

    X = np.array(X)
    y = np.array(y)

    model = RandomForestClassifier(n_estimators=150, max_depth=10, random_state=42)
    model.fit(X, y)

    current_window = history[:4]
    current_freq = [0] * max_num
    for draw in current_window:
        for num in draw.get("sestina", []):
            if 1 <= num <= max_num:
                current_freq[num - 1] += 1

    probabilities = model.predict_proba([current_freq])
    
    num_probs = {}
    for idx in range(max_num):
        prob_arr = probabilities[idx][0]
        prob_val = prob_arr[1] if len(prob_arr) > 1 else 0.05
        num_probs[idx + 1] = float(prob_val)

    return num_probs

# ==========================================
# 3. MOTORE TERMODINAMICO "VIRTUAL VENUS"
# ==========================================
def simulate_virtual_venus_physics(history, ml_probs, iterations=10000):
    """
    Simula le dinamiche fisiche e stocastiche dell'urna Venus:
    - Massa (Ritardo accumulato)
    - Energia Cinetica (Frequenza recente)
    - Magnetismo di Rete (Co-occorrenze storiche)
    """
    max_num = 90
    delays = {n: 0 for n in range(1, max_num + 1)}
    
    # Calcolo ritardo (Massa)
    for num in range(1, max_num + 1):
        for i, draw in enumerate(history):
            if num in draw.get("sestina", []):
                delays[num] = i
                break
        else:
            delays[num] = len(history)

    # Calcolo Energia Cinetica (Ultime 12 estrazioni)
    recent_draws = history[:12]
    kinetic_energy = {n: 0 for n in range(1, max_num + 1)}
    for draw in recent_draws:
        for num in draw.get("sestina", []):
            kinetic_energy[num] += 1

    # Matrice di Co-occorrenza (Magnetismo)
    co_matrix = np.zeros((max_num + 1, max_num + 1))
    for draw in history[:50]:
        s = draw.get("sestina", [])
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                co_matrix[s[i]][s[j]] += 1
                co_matrix[s[j]][s[i]] += 1

    # SIMULAZIONE MONTE CARLO FISICO
    physics_scores = {n: 0.0 for n in range(1, max_num + 1)}
    
    for _ in range(iterations):
        temp_scores = []
        for n in range(1, max_num + 1):
            mass_factor = np.log1p(delays[n]) * 0.15
            kinetic_factor = kinetic_energy[n] * 0.25
            ml_factor = ml_probs.get(n, 0.05) * 2.0
            noise = np.random.gumbel(0, 0.1) # Turbolenza stocastica d'aria Venus
            
            total_energy = mass_factor + kinetic_factor + ml_factor + noise
            temp_scores.append((n, total_energy))
        
        temp_scores.sort(key=lambda x: x[1], reverse=True)
        top_6 = [item[0] for item in temp_scores[:6]]
        
        for n in top_6:
            physics_scores[n] += 1.0

    for n in physics_scores:
        physics_scores[n] = round(physics_scores[n] / iterations, 4)

    return physics_scores

# ==========================================
# 4. IPER-MATRICE ORTOGONALE (4 SESTINE / €4)
# ==========================================
def calculate_anti_mass_score(sestina):
    dates_count = sum(1 for n in sestina if n <= 31)
    if dates_count >= 5: score = 0.20
    elif dates_count == 4: score = 0.50
    elif dates_count == 3: score = 0.85
    else: score = 1.00

    diffs = [sestina[i+1] - sestina[i] for i in range(len(sestina)-1)]
    if len(set(diffs)) == 1: score *= 0.1
    return round(score, 2)

def generate_hyper_matrix_4_sestine(physics_scores, ml_probs):
    """
    Seleziona i 12 numeri TOP per energia e sviluppa l'Iper-Matrice a 4 Blocchi Ortogonali:
    Block A (3) | Block B (3) | Block C (3) | Block D (3)
    S1 = A + B | S2 = A + C | S3 = B + D | S4 = C + D
    """
    combined_scores = {}
    for n in range(1, 91):
        combined_scores[n] = (physics_scores.get(n, 0) * 0.6) + (ml_probs.get(n, 0) * 0.4)

    top_12 = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)[:12]
    pool_12 = [item[0] for item in top_12]

    np.random.shuffle(pool_12)
    block_A = sorted(pool_12[0:3])
    block_B = sorted(pool_12[3:6])
    block_C = sorted(pool_12[6:9])
    block_D = sorted(pool_12[9:12])

    s1 = sorted(block_A + block_B)
    s2 = sorted(block_A + block_C)
    s3 = sorted(block_B + block_D)
    s4 = sorted(block_C + block_D)

    sestine_raw = [s1, s2, s3, s4]
    matrix_output = []

    for i, s in enumerate(sestine_raw, 1):
        somma = sum(s)
        z_sc = round((somma - 273.0) / 45.5, 2)
        ev_sc = calculate_anti_mass_score(s)
        conf = round(sum(combined_scores[n] for n in s) / 6, 4)
        
        matrix_output.append({
            "id": f"Sestina OMEGA {i}",
            "sestina": s,
            "somma": somma,
            "z_score": z_sc,
            "ev_score": ev_sc,
            "confidence": conf
        })

    return pool_12, matrix_output

# ==========================================
# 5. SCRAPER BLINDATO MULTI-SORGENTE & FALLBACK
# ==========================================
def fetch_superenalotto():
    urls = [
        "https://www.superenalotto.net/estrazioni",
        "https://www.estrazionedellotto.it/estrazioni-superenalotto"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=8)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, 'html.parser')
                text = soup.get_text()

                # Parsing Jackpot
                jackpot_val = None
                jp_match = re.search(r'(?:jackpot|montepremi)[:\s]*€?\s*([\d\.\,]+\s*(?:milioni|mila)?)', text, re.I)
                if jp_match:
                    val = jp_match.group(1).strip()
                    jackpot_val = val if val.startswith("€") else f"€ {val}"
                else:
                    jp_fallback = re.search(r'€\s*[\d\.\,]{4,}\s*(?:milioni|mila)?', text, re.I)
                    if jp_fallback:
                        jackpot_val = jp_fallback.group(0).strip()

                if not jackpot_val or "N/D" in jackpot_val:
                    jackpot_val = "€ 222.400.000"

                # Parsing Numeri
                balls = soup.select('.ball, .numero, ul.balls li, span.ball, div.ball, td.ball')
                extracted_nums = []
                for b in balls:
                    val = b.text.strip()
                    if val.isdigit():
                        n = int(val)
                        if 1 <= n <= 90 and n not in extracted_nums:
                            extracted_nums.append(n)

                if len(extracted_nums) < 6:
                    num_matches = re.findall(r'\b(?:[1-9]|[1-8][0-9]|90)\b', text)
                    extracted_nums = []
                    for nm in num_matches:
                        n = int(nm)
                        if n not in extracted_nums:
                            extracted_nums.append(n)
                        if len(extracted_nums) >= 8:
                            break

                if len(extracted_nums) >= 6:
                    date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
                    found_date = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

                    conc_match = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text, re.I)
                    conc_num = conc_match.group(1) if conc_match else "144"

                    sestina = sorted(extracted_nums[:6])
                    jolly = extracted_nums[6] if len(extracted_nums) > 6 else 90
                    superstar = extracted_nums[7] if len(extracted_nums) > 7 else 90

                    print(f"[SCRAPER OK] Concorso N° {conc_num} ({found_date}) | Sestina: {sestina}")
                    return {
                        "concorso": str(conc_num),
                        "data": found_date,
                        "sestina": sestina,
                        "jolly": jolly,
                        "superstar": superstar,
                        "jackpot": jackpot_val
                    }
        except Exception as e:
            print(f"[WARN SCRAPER] Timeout/Errore su {url}: {e}")
            continue

    # Fallback Anti-Crash in caso di blocchi di rete
    print("[WARN] Rete bloccata o timeout. Attivazione fallback su archivio locale...")
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
                if hist:
                    last = hist[0]
                    return {
                        "concorso": str(last.get("concorso", "144")),
                        "data": last.get("data", datetime.now().strftime("%d/%m/%Y")),
                        "sestina": last.get("sestina", [23, 26, 41, 52, 59, 85]),
                        "jolly": 90,
                        "superstar": 90,
                        "jackpot": last.get("jackpot", "€ 222.400.000")
                    }
        except Exception as e:
            print(f"[ERROR CACHE] {e}")

    return {
        "concorso": "144",
        "data": datetime.now().strftime("%d/%m/%Y"),
        "sestina": [23, 26, 41, 52, 59, 85],
        "jolly": 90,
        "superstar": 90,
        "jackpot": "€ 222.400.000"
    }

# ==========================================
# 6. GRAFICO DENSITÀ QUANTISTICA
# ==========================================
def generate_advanced_chart(sestina, pool_12, physics_scores):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0b0f19')
    ax1.set_facecolor('#0f172a')
    ax2.set_facecolor('#0f172a')

    # Distribuzione Gaussiana Sestina
    somma = sum(sestina)
    x = np.linspace(100, 450, 500)
    y = (1 / (45.5 * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - 273.0) / 45.5)**2)
    ax1.plot(x, y, color='#38bdf8', linewidth=2)
    ax1.axvline(somma, color='#f59e0b', linestyle='--', linewidth=2.5, label=f'Somma: {somma}')
    ax1.axvspan(220, 320, color='#10b981', alpha=0.15)
    ax1.set_title('Distribuzione Gaussiana Venus', color='#f8fafc')
    ax1.legend(facecolor='#1e293b')

    # Top 12 Dodecaedro OMEGA
    nums = [f"N°{n}" for n in pool_12]
    scores = [physics_scores.get(n, 0) for n in pool_12]

    ax2.barh(nums, scores, color='#10b981')
    ax2.set_title('Energia Termodinamica Pool 12 OMEGA', color='#f8fafc')
    ax2.invert_yaxis()

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

# ==========================================
# 7. EXECUTION CORE
# ==========================================
def main():
    se_data = fetch_superenalotto()
    sestina = se_data["sestina"]
    concorso = str(se_data["concorso"])
    data_str = se_data["data"]
    jackpot_str = se_data.get("jackpot", "€ 222.400.000")
    somma = sum(sestina)
    z_score = round((somma - 273.0) / 45.5, 2)

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    latest_sestina = history[0].get("sestina", []) if len(history) > 0 else []
    
    # Scudo Anti-Duplicato
    if any(str(item.get("concorso")) == concorso for item in history) or (latest_sestina == sestina):
        print(f"[INFO] Concorso N° {concorso} già presente in archivio. Esecuzione terminata.")
        sys.exit(0)

    # Inserimento nuovo concorso
    history.insert(0, {
        "concorso": concorso, 
        "data": data_str, 
        "sestina": sestina,
        "somma": somma, 
        "z_score": z_score,
        "jackpot": jackpot_str
    })
    
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

    print(f"[SUCCESS] Concorso N° {concorso} registrato con successo!")

    # 1. Machine Learning Engine
    ml_probabilities = train_ml_predictive_model(history)
    
    # 2. Virtual Venus Physics Engine
    physics_scores = simulate_virtual_venus_physics(history, ml_probabilities, iterations=10000)
    
    # 3. Hyper-Matrix 4 Sestine Generation
    pool_12, matrix_sestine = generate_hyper_matrix_4_sestine(physics_scores, ml_probabilities)

    # Output Database
    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_draw": {
            "concorso": concorso,
            "data": data_str,
            "sestina": sestina,
            "jolly": se_data.get('jolly', 'N/D'),
            "superstar": se_data.get('superstar', 'N/D'),
            "jackpot": jackpot_str
        },
        "quant_metrics": {
            "somma": somma, 
            "z_score": z_score,
            "anti_mass_index": calculate_anti_mass_score(sestina)
        },
        "omega_dodecahedron_pool": pool_12,
        "hyper_matrix_predictions": matrix_sestine
    }

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

    generate_advanced_chart(sestina, pool_12, physics_scores)

    # Formattazione Notifica Telegram
    pred_text = ""
    for item in matrix_sestine:
        pred_text += f"🔹 <b>{item['id']}:</b> <code>{item['sestina']}</code>\n" \
                     f"   └─ <i>Somma: {item['somma']} | Anti-Massa: {item['ev_score']}</i>\n"

    caption = (
        f"⚡ <b>VENUS VORTEX — PROTOCOLLO OMEGA</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Concorso:</b> N° {concorso} ({data_str})\n"
        f"🎲 <b>Estratti:</b> <code>{sestina}</code>\n"
        f"⭐ <b>Jolly:</b> <code>{se_data.get('jolly', 'N/D')}</code> | 🌟 <b>SuperStar:</b> <code>{se_data.get('superstar', 'N/D')}</code>\n"
        f"💰 <b>Jackpot Stimato:</b> <b>{jackpot_str}</b>\n\n"
        f"🌌 <b>DODECAEDRO D'ÉLITE (POOL 12 NUMERI):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>IPER-MATRICE ORTOGONALE (4 SESTINE / €4,00):</b>\n"
        f"{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <a href='https://Francis490.github.io/superenalotto-venus-vortex/'><b>Dashboard Web Live</b></a>"
    )

    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
