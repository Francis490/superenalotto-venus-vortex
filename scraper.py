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
# 1. TELEGRAM ENGINE
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
                print("[TELEGRAM] Report e grafico ML inviati con successo su Telegram!")
            else:
                print(f"[TELEGRAM ERROR] Risposta API {resp.status_code}: {resp.text}")
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

    model = RandomForestClassifier(n_estimators=100, random_state=42)
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
        if len(prob_arr) > 1:
            prob_val = prob_arr[1]
        else:
            prob_val = 0.05
        num_probs[idx + 1] = float(prob_val)

    return num_probs

# ==========================================
# 3. TEORIA DEI GIOCHI & ANTI-MASSA
# ==========================================
def calculate_anti_mass_score(sestina):
    dates_count = sum(1 for n in sestina if n <= 31)
    if dates_count >= 5:
        score = 0.20
    elif dates_count == 4:
        score = 0.50
    elif dates_count == 3:
        score = 0.85
    else:
        score = 1.00

    diffs = [sestina[i+1] - sestina[i] for i in range(len(sestina)-1)]
    if len(set(diffs)) == 1:
        score *= 0.1
    return round(score, 2)

def generate_hybrid_predictions(ml_probs, count=3):
    predictions = []
    attempts = 0
    
    all_numbers = list(range(1, 91))
    weights = [ml_probs.get(n, 0.01) for n in all_numbers]

    while len(predictions) < count and attempts < 20000:
        attempts += 1
        
        candidate = []
        temp_numbers = list(all_numbers)
        temp_weights = list(weights)
        
        for _ in range(6):
            chosen = random.choices(temp_numbers, weights=temp_weights, k=1)[0]
            idx = temp_numbers.index(chosen)
            candidate.append(chosen)
            temp_numbers.pop(idx)
            temp_weights.pop(idx)
            
        candidate = sorted(candidate)
        somma = sum(candidate)
        anti_mass_score = calculate_anti_mass_score(candidate)

        has_high_number = any(n > 50 for n in candidate)

        if attempts < 10000:
            if not (200 <= somma <= 340):
                continue
            if anti_mass_score < 0.75:
                continue
            if not has_high_number:
                continue

        if candidate not in [p["sestina"] for p in predictions]:
            predictions.append({
                "sestina": candidate,
                "ev_score": anti_mass_score,
                "ml_confidence": round(sum(ml_probs.get(n, 0.05) for n in candidate) / 6, 4)
            })

    if len(predictions) < count:
        while len(predictions) < count:
            cand = sorted(random.sample(range(1, 91), 6))
            if cand not in [p["sestina"] for p in predictions]:
                predictions.append({
                    "sestina": cand,
                    "ev_score": calculate_anti_mass_score(cand),
                    "ml_confidence": 0.05
                })

    return predictions

# ==========================================
# 4. SCRAPER BLINDATO & PARSING DATA
# ==========================================
def fetch_superenalotto():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    url = "https://www.superenalotto.net/estrazioni"
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            
            # Parsing Jackpot
            jackpot_val = "N/D"
            jp_match = re.search(r'(?:jackpot|montepremi)[:\s]*€?\s*([\d\.\,]+\s*(?:milioni|mila)?)', text, re.I)
            if jp_match:
                jackpot_val = jp_match.group(1).strip()
                if not jackpot_val.startswith("€"):
                    jackpot_val = f"€ {jackpot_val}"
            else:
                jp_fallback = re.search(r'€\s*[\d\.\,]{4,}\s*(?:milioni|mila)?', text, re.I)
                if jp_fallback:
                    jackpot_val = jp_fallback.group(0).strip()

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
                conc_match = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text, re.I)
                
                found_date = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")
                conc_num = conc_match.group(1) if conc_match else found_date.replace("/", "")
                
                sestina = sorted(extracted_nums[:6])
                jolly = extracted_nums[6] if len(extracted_nums) > 6 else 90
                superstar = extracted_nums[7] if len(extracted_nums) > 7 else 90

                print(f"[SCRAPER] Concorso {conc_num} ({found_date}) | Sestina: {sestina} | Jackpot: {jackpot_val}")
                return {
                    "concorso": str(conc_num),
                    "data": found_date,
                    "sestina": sestina,
                    "jolly": jolly,
                    "superstar": superstar,
                    "jackpot": jackpot_val
                }
    except Exception as e:
        print(f"[ERROR SCRAPER] {e}")

    print("[CRITICAL] Impossibile estrarre i dati online. Arresto preventivo.")
    sys.exit(1)

def generate_advanced_chart(sestina, somma, z_score, ml_probs):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0b0f19')
    ax1.set_facecolor('#0f172a')
    ax2.set_facecolor('#0f172a')

    x = np.linspace(100, 450, 500)
    y = (1 / (45.5 * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - 273.0) / 45.5)**2)
    ax1.plot(x, y, color='#38bdf8', linewidth=2)
    ax1.axvline(somma, color='#f59e0b', linestyle='--', linewidth=2.5, label=f'Somma: {somma}')
    ax1.axvspan(220, 320, color='#10b981', alpha=0.15)
    ax1.set_title(f'Gaussiana (Z-Score: {z_score})', color='#f8fafc')
    ax1.legend(facecolor='#1e293b')

    top_ml = sorted(ml_probs.items(), key=lambda k: k[1], reverse=True)[:10]
    nums = [f"N°{k}" for k, v in top_ml]
    probs = [v for k, v in top_ml]

    ax2.barh(nums, probs, color='#a855f7')
    ax2.set_title('Top 10 ML Confidence Index', color='#f8fafc')
    ax2.invert_yaxis()

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

# ==========================================
# 5. CORE EXECUTION
# ==========================================
def main():
    se_data = fetch_superenalotto()
    sestina = se_data["sestina"]
    concorso = str(se_data["concorso"])
    data_str = se_data["data"]
    jackpot_str = se_data.get("jackpot", "N/D")
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
    
    # SCUDO VETTORIALE ANTI-DUPLICATO E ANTI-CACHE
    estrazione_gia_presente = (
        any(str(item.get("concorso")) == concorso for item in history) or
        (latest_sestina == sestina)
    )

    if estrazione_gia_presente:
        print(f"[INFO] Concorso {concorso} o Sestina {sestina} già presente in archivio. Esecuzione terminata senza modifiche.")
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

    print(f"[SUCCESS] Concorso {concorso} registrato con successo!")

    ml_probabilities = train_ml_predictive_model(history)
    predictions = generate_hybrid_predictions(ml_probabilities)

    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_draw": se_data,
        "quant_metrics": {
            "somma": somma, 
            "z_score": z_score,
            "anti_mass_index": calculate_anti_mass_score(sestina)
        },
        "ml_predictions": predictions
    }

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2, ensure_ascii=False)

    generate_advanced_chart(sestina, somma, z_score, ml_probabilities)

    pred_text = ""
    for p in predictions:
        pred_text += f"🎯 <code>{p['sestina']}</code> | Anti-Massa EV: <b>{p['ev_score']}</b>\n"

    caption = (
        f"⚡ <b>VENUS VORTEX — DIVINE ML ENGINE</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Concorso:</b> {concorso} ({data_str})\n"
        f"🎲 <b>Sestina:</b> <code>{sestina}</code>\n"
        f"⭐ <b>Jolly:</b> <code>{se_data.get('jolly', 'N/D')}</code> | 🌟 <b>SuperStar:</b> <code>{se_data.get('superstar', 'N/D')}</code>\n"
        f"💰 <b>Jackpot Stimato:</b> <b>{jackpot_str}</b>\n"
        f"📊 <b>Somma:</b> <code>{somma}</code> (Z-Score: <code>{z_score}</code>)\n"
        f"👁️ <b>Anti-Massa Score:</b> <code>{calculate_anti_mass_score(sestina)}</code>\n\n"
        f"🧠 <b>PREVISIONI MACHINE LEARNING (RANDOM FOREST):</b>\n"
        f"{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <a href='https://Francis490.github.io/superenalotto-venus-vortex/'><b>Dashboard Web Live</b></a>"
    )

    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
