import os
import re
import json
import math
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
        print("[WARN] Credenziali Telegram assenti.")
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
                print("[TELEGRAM] Report e grafico ML inviati con successo!")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

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
        prob_val = probabilities[idx][0][1] if len(probabilities[idx][0]) > 1 else 0.05
        num_probs[idx + 1] = float(prob_val)

    return num_probs

# ==========================================
# 3. TEORIA DEI GIOCHI & ANTI-MASSA
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

def generate_hybrid_predictions(ml_probs, count=3):
    predictions = []
    attempts = 0
    ranked_numbers = sorted(ml_probs.keys(), key=lambda k: ml_probs[k], reverse=True)
    candidate_pool = ranked_numbers[:35]

    while len(predictions) < count and attempts < 10000:
        attempts += 1
        candidate = sorted(random.sample(candidate_pool, 6))
        
        somma = sum(candidate)
        if not (220 <= somma <= 320): continue

        anti_mass_score = calculate_anti_mass_score(candidate)
        if anti_mass_score < 0.80: continue

        if candidate not in [p["sestina"] for p in predictions]:
            predictions.append({
                "sestina": candidate,
                "ev_score": anti_mass_score,
                "ml_confidence": round(sum(ml_probs[n] for n in candidate) / 6, 4)
            })
    return predictions

# ==========================================
# 4. SCRAPER & GRAFICA
# ==========================================
def fetch_superenalotto():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    res = requests.get("https://www.superenalotto.net/estrazioni", headers=headers, timeout=15)
    if res.status_code == 200:
        soup = BeautifulSoup(res.text, 'html.parser')
        text = soup.get_text()
        conc = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text, re.I)
        date = re.search(r'(\d{2}/\d{2}/\d{4})', text)

        # Estrazione mirata dei soli numeri della combinazione vincente
        raw_numbers = []
        for tag in soup.find_all(['li', 'span', 'div'], class_=re.compile(r'ball|numero|win', re.I)):
            val = tag.text.strip()
            if val.isdigit():
                num = int(val)
                if 1 <= num <= 90 and num not in raw_numbers:
                    raw_numbers.append(num)

        # Seleziona esattamente i primi 6 numeri unici per la sestina
        if len(raw_numbers) >= 6:
            sestina = sorted(raw_numbers[:6])
            jolly = raw_numbers[6] if len(raw_numbers) > 6 else None
            superstar = raw_numbers[7] if len(raw_numbers) > 7 else None
            
            found_date = date.group(1) if date else "01/09/2026"
            return {
                "concorso": conc.group(1) if conc else found_date.replace("/", ""),
                "data": found_date,
                "sestina": sestina,
                "jolly": jolly,
                "superstar": superstar
            }
            
    raise Exception("Impossibile recuperare i dati ufficiali dell'estrazione.")

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
    concorso = se_data["concorso"]
    data_str = se_data["data"]
    somma = sum(sestina)
    z_score = round((somma - 273.0) / 45.5, 2)

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception: history = []

    if not any(item.get("concorso") == concorso for item in history):
        history.insert(0, {
            "concorso": concorso, "data": data_str, "sestina": sestina,
            "somma": somma, "z_score": z_score
        })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    ml_probabilities = train_ml_predictive_model(history)
    predictions = generate_hybrid_predictions(ml_probabilities)

    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_draw": se_data,
        "quant_metrics": {
            "somma": somma, "z_score": z_score,
            "anti_mass_index": calculate_anti_mass_score(sestina)
        },
        "ml_predictions": predictions
    }

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2)

    generate_advanced_chart(sestina, somma, z_score, ml_probabilities)

    pred_text = ""
    for idx, p in enumerate(predictions):
        pred_text += f"🎯 <code>{p['sestina']}</code> | Anti-Massa EV: <b>{p['ev_score']}</b>\n"

    caption = (
        f"⚡ <b>VENUS VORTEX — DIVINE ML ENGINE</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Concorso:</b> {concorso} ({data_str})\n"
        f"🎲 <b>Sestina:</b> <code>{sestina}</code>\n"
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
