import os
import re
import json
import math
import html
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import matplotlib
matplotlib.use('Agg') # Rendering headless per server cloud
import matplotlib.pyplot as plt
import numpy as np

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"

# ==========================================
# 1. TELEGRAM MEDIA ENGINE
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
            files = {"photo": photo}
            resp = requests.post(url, data=payload, files=files, timeout=25)
            if resp.status_code == 200:
                print("[TELEGRAM] Grafico e Report inviati con successo!")
            else:
                print(f"[TELEGRAM ERROR] {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Fallimento invio media: {e}")

# ==========================================
# 2. GENERATORE DI GRAFICI ANALITICI (MATPLOTLIB)
# ==========================================
def generate_vortex_chart(sestina, somma, z_score, hot_nums, cold_nums):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), facecolor='#0b0f19')
    ax1.set_facecolor('#0f172a')
    ax2.set_facecolor('#0f172a')

    # Grafico 1: Distribuzione Gaussiana della Somma
    x = np.linspace(100, 450, 500)
    mu, sigma = 273.0, 45.5
    y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mu) / sigma)**2)
    
    ax1.plot(x, y, color='#38bdf8', linewidth=2, label='Curva Teorica')
    ax1.axvline(somma, color='#f59e0b', linestyle='--', linewidth=2.5, label=f'Somma Attuale: {somma}')
    ax1.axvspan(220, 320, color='#10b981', alpha=0.15, label='Range Gaussiano OK')
    ax1.set_title(f'Distribuzione Gaussiana (Z-Score: {z_score})', color='#f8fafc', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Somma Sestina', color='#94a3b8')
    ax1.legend(loc='upper right', facecolor='#1e293b', edgecolor='#334155')
    ax1.grid(True, color='#1e293b', linestyle=':')

    # Grafico 2: Top Frequenti vs Ritardatari
    categories = ['Top Frequenti', 'Top Ritardi']
    hot_str = ", ".join(map(str, hot_nums[:5]))
    cold_str = ", ".join(map(str, cold_nums[:5]))
    
    ax2.barh(['Ritardatari', 'Frequenti'], [len(cold_nums[:5]), len(hot_nums[:5])], color=['#a855f7', '#38bdf8'])
    ax2.set_title('Top 5 Frequenze vs Ritardi', color='#f8fafc', fontsize=12, fontweight='bold')
    ax2.text(0.5, 1, f"HOT: {hot_str}", color='#38bdf8', fontsize=10, fontweight='bold', va='center')
    ax2.text(0.5, 0, f"COLD: {cold_str}", color='#a855f7', fontsize=10, fontweight='bold', va='center')
    ax2.grid(True, color='#1e293b', linestyle=':')

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()

# ==========================================
# 3. MOTORE MARKOV & MONTE CARLO (10.000 ITERAZIONI)
# ==========================================
def calculate_shannon_entropy(sestina):
    freq = {}
    for num in sestina:
        dec = (num - 1) // 10
        freq[dec] = freq.get(dec, 0) + 1
    entropy = 0.0
    for count in freq.values():
        p = count / 6.0
        entropy -= p * math.log2(p)
    return round(entropy, 3)

def generate_monte_carlo_predictions(history, hot_nums, cold_nums, runs=10000):
    weights = np.ones(91)
    
    # Assegna pesi probabilistici
    for n in hot_nums[:15]: weights[n] += 1.5
    for n in cold_nums[:15]: weights[n] += 2.0
    
    # Matrice di transizione Markov (Sull'ultimo concorso)
    if history:
        last_draw = history[0].get("sestina", [])
        for n in last_draw:
            for neighbor in range(max(1, n-2), min(91, n+3)):
                weights[neighbor] += 0.8
                
    probabilities = weights[1:] / np.sum(weights[1:])
    
    valid_predictions = []
    candidates_seen = set()

    for _ in range(runs):
        sample = np.random.choice(range(1, 91), size=6, replace=False, p=probabilities)
        sample = tuple(sorted(sample))
        
        if sample in candidates_seen:
            continue
        candidates_seen.add(sample)

        s_val = sum(sample)
        if 220 <= s_val <= 320:
            evens = sum(1 for x in sample if x % 2 == 0)
            if evens in [2, 3, 4]:
                valid_predictions.append(list(sample))
                if len(valid_predictions) == 3:
                    break

    return valid_predictions

# ==========================================
# 4. SCRAPING REDONDANTE
# ==========================================
def fetch_latest_draw():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        res = requests.get("https://www.superenalotto.net/estrazioni", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            conc = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text, re.I)
            date = re.search(r'(\d{2}/\d{2}/\d{4})', text)

            concorso = conc.group(1) if conc else datetime.now().strftime("%Y%m%d")
            data_str = date.group(1) if date else datetime.now().strftime("%d/%m/%Y")

            numbers = []
            for tag in soup.find_all(['li', 'span', 'td']):
                val = tag.text.strip()
                if val.isdigit() and 1 <= int(val) <= 90:
                    cls = " ".join(tag.get('class', []))
                    if any(k in cls.lower() for k in ['ball', 'numero', 'sym']):
                        numbers.append(int(val))

            if len(numbers) < 6:
                raw_nums = re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', res.text)
                clean_seq = []
                for n in [int(x) for x in raw_nums]:
                    if len(clean_seq) < 6 and n not in clean_seq:
                        clean_seq.append(n)
                numbers = clean_seq

            if len(numbers) >= 6:
                return concorso, data_str, sorted(numbers[:6]), numbers[6] if len(numbers)>6 else None, numbers[7] if len(numbers)>7 else None
    except Exception as e:
        print(f"[WARN] Fonte 1 fallita: {e}")

    raise Exception("Impossibile scaricare l'estrazione.")

# ==========================================
# 5. CORE EXECUTION
# ==========================================
def main():
    concorso, data_str, sestina, jolly, star = fetch_latest_draw()
    somma = sum(sestina)
    z_score = round((somma - 273.0) / 45.5, 2)
    entropy = calculate_shannon_entropy(sestina)
    in_range = 220 <= somma <= 320

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception: history = []

    if not any(item.get("concorso") == concorso for item in history):
        history.insert(0, {
            "concorso": concorso, "data": data_str, "sestina": sestina,
            "somma": somma, "jolly": jolly, "superstar": star,
            "entropy": entropy, "z_score": z_score
        })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    # Calcolo Frequenze e Ritardi
    freq_map = {i: 0 for i in range(1, 91)}
    delay_map = {i: 0 for i in range(1, 91)}
    for idx, draw in enumerate(history):
        s = draw.get("sestina", [])
        for n in range(1, 91):
            if n in s: freq_map[n] += 1
            elif idx == 0 or delay_map[n] == idx: delay_map[n] = idx + 1

    sorted_hot = sorted(freq_map.keys(), key=lambda x: freq_map[x], reverse=True)
    sorted_cold = sorted(delay_map.keys(), key=lambda x: delay_map[x], reverse=True)

    # Monte Carlo Matrix
    predictions = generate_monte_carlo_predictions(history, sorted_hot, sorted_cold)

    # Output JSON Database
    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_draw": {
            "concorso": concorso, "data": data_str, "sestina": sestina,
            "somma": somma, "in_gaussian_range": in_range, "z_score": z_score,
            "shannon_entropy": entropy, "jolly": jolly, "superstar": star
        },
        "analytics": {
            "hot_numbers_top10": sorted_hot[:10],
            "cold_numbers_top10": sorted_cold[:10],
            "predictions_next_draw": predictions
        },
        "history_summary": history[:20]
    }

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2)

    # Genera Immagine Grafica
    generate_vortex_chart(sestina, somma, z_score, sorted_hot, sorted_cold)

    # Telegram Report
    pred_str = "\n".join([f"🎯 <code>{p}</code>" for p in predictions])
    caption = (
        f"⚡ <b>VENUS VORTEX — QUANTUM REPORT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Concorso:</b> {concorso} del {data_str}\n"
        f"🎲 <b>Sestina:</b> <code>{sestina}</code>\n"
        f"📊 <b>Somma:</b> <code>{somma}</code> (Z-Score: <code>{z_score}</code>)\n"
        f"🌀 <b>Entropia:</b> <code>{entropy} bits</code>\n\n"
        f"🔥 <b>HOT:</b> {sorted_hot[:5]}\n"
        f"🧊 <b>COLD:</b> {sorted_cold[:5]}\n\n"
        f"🔮 <b>PREVISIONI MARKOV & MONTE CARLO:</b>\n"
        f"{pred_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <a href='https://Francis490.github.io/superenalotto-venus-vortex/'><b>Dashboard Web Live</b></a>"
    )

    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
