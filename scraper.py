import os
import re
import json
import math
import html
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"

# ==========================================
# 1. FUNZIONALITÀ TELEGRAM
# ==========================================
def send_telegram_alert(html_message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Credenziali Telegram assenti.")
        return

    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"):
        token = token[3:]

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID.strip(),
        "text": html_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print("[TELEGRAM] Notifica inviata con successo.")
        else:
            print(f"[TELEGRAM ERROR] Status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")

# ==========================================
# 2. CALCOLI MATEMATICI & STATISTICI AVANZATI
# ==========================================
def calculate_shannon_entropy(sestina):
    """Calcola l'entropia della distribuzione dei numeri estratti."""
    freq = {}
    for num in sestina:
        dec = (num - 1) // 10
        freq[dec] = freq.get(dec, 0) + 1
    
    entropy = 0.0
    for count in freq.values():
        p = count / 6.0
        entropy -= p * math.log2(p)
    return round(entropy, 3)

def calculate_z_score(somma):
    """Calcola lo Z-Score della somma rispetto alla media teorica del SuperEnalotto (273)."""
    media_teorica = 273.0
    deviazione_std = 45.5
    return round((somma - media_teorica) / deviazione_std, 2)

def generate_vortex_predictions(history, hot_numbers, cold_numbers):
    """Algoritmo Generativo Quantitativo per le prossime Sestine."""
    predictions = []
    attempts = 0
    
    # Pool bilanciato: Top Hot + Top Cold + Neutri
    pool = list(set(hot_numbers[:20] + cold_numbers[:20] + random.sample(range(1, 91), 30)))

    while len(predictions) < 3 and attempts < 5000:
        attempts += 1
        candidate = sorted(random.sample(pool, 6))
        s_val = sum(candidate)
        
        # Filtro 1: Somma Gaussiana (220-320)
        if not (220 <= s_val <= 320):
            continue
            
        # Filtro 2: Pari / Dispari
        evens = sum(1 for x in candidate if x % 2 == 0)
        if evens not in [2, 3, 4]:
            continue

        # Filtro 3: Max 2 numeri per Decina
        decades = [(x - 1) // 10 for x in candidate]
        if any(decades.count(d) > 2 for d in set(decades)):
            continue

        # Filtro 4: Nessun terno consecutivo
        consec = False
        for i in range(len(candidate) - 2):
            if candidate[i+1] == candidate[i] + 1 and candidate[i+2] == candidate[i] + 2:
                consec = True
                break
        if consec:
            continue

        if candidate not in predictions:
            predictions.append(candidate)

    return predictions

# ==========================================
# 3. SCRAPING ENGINE REDONDANTE
# ==========================================
def fetch_latest_draw():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    # FONTE 1: SuperEnalotto.net
    try:
        print("[SCRAPER] Fonte 1: SuperEnalotto.net...")
        res = requests.get("https://www.superenalotto.net/estrazioni", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text_block = soup.get_text()

            conc_match = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text_block, re.IGNORECASE)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text_block)

            concorso = conc_match.group(1) if conc_match else datetime.now().strftime("%Y%m%d")
            data_str = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

            numbers = []
            for tag in soup.find_all(['li', 'span', 'td']):
                val = tag.text.strip()
                if val.isdigit() and 1 <= int(val) <= 90:
                    parent_class = " ".join(tag.get('class', []))
                    if any(k in parent_class.lower() for k in ['ball', 'numero', 'sym']):
                        numbers.append(int(val))

            if len(numbers) < 6:
                raw_nums = re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', res.text)
                clean_seq = []
                for n in [int(x) for x in raw_nums]:
                    if len(clean_seq) < 6 and n not in clean_seq:
                        clean_seq.append(n)
                numbers = clean_seq

            if len(numbers) >= 6:
                sestina = sorted(numbers[:6])
                jolly = numbers[6] if len(numbers) > 6 else None
                star = numbers[7] if len(numbers) > 7 else None
                return concorso, data_str, sestina, jolly, star
    except Exception as e:
        print(f"[WARN] Fonte 1 fallita: {e}")

    # FONTE 2: Agimeg.it
    try:
        print("[SCRAPER] Fonte 2: Agimeg.it...")
        res = requests.get("https://www.agimeg.it/estrazioni-superenalotto/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            page_text = soup.get_text()

            conc_match = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', page_text, re.IGNORECASE)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', page_text)

            concorso = conc_match.group(1) if conc_match else "N/D"
            data_str = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

            sestina_match = re.search(r'(?:sestina|combinazione|numeri estratti)[^\d]*(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})', page_text, re.IGNORECASE)
            if sestina_match:
                sestina = sorted([int(sestina_match.group(i)) for i in range(1, 7)])
                return concorso, data_str, sestina, None, None
    except Exception as e:
        print(f"[WARN] Fonte 2 fallita: {e}")

    raise Exception("Nessuna fonte dati disponibile.")

# ==========================================
# 4. AGGREGATORE E CORE SYNC
# ==========================================
def main():
    concorso, data_str, sestina, jolly, star = fetch_latest_draw()
    somma = sum(sestina)
    in_range = 220 <= somma <= 320
    entropy = calculate_shannon_entropy(sestina)
    z_score = calculate_z_score(somma)

    # Carica o Inizializza lo Storico
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    # Aggiungi nuova estrazione se non presente
    if not any(item.get("concorso") == concorso for item in history):
        history.insert(0, {
            "concorso": concorso,
            "data": data_str,
            "sestina": sestina,
            "somma": somma,
            "jolly": jolly,
            "superstar": star,
            "entropy": entropy,
            "z_score": z_score
        })
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    # Calcolo Frequenze e Ritardi su tutto lo storico
    freq_map = {i: 0 for i in range(1, 91)}
    delay_map = {i: 0 for i in range(1, 91)}
    
    for idx, draw in enumerate(history):
        s = draw.get("sestina", [])
        for n in range(1, 91):
            if n in s:
                freq_map[n] += 1
            elif idx == 0 or delay_map[n] == idx:
                delay_map[n] = idx + 1

    sorted_hot = sorted(freq_map.keys(), key=lambda x: freq_map[x], reverse=True)
    sorted_cold = sorted(delay_map.keys(), key=lambda x: delay_map[x], reverse=True)

    # Genera Previsioni per il prossimo concorso
    predictions = generate_vortex_predictions(history, sorted_hot, sorted_cold)

    # Prepara Database JSON per API / Frontend
    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_draw": {
            "concorso": concorso,
            "data": data_str,
            "sestina": sestina,
            "somma": somma,
            "in_gaussian_range": in_range,
            "z_score": z_score,
            "shannon_entropy": entropy,
            "jolly": jolly,
            "superstar": star
        },
        "analytics": {
            "hot_numbers_top10": sorted_hot[:10],
            "cold_numbers_top10": sorted_cold[:10],
            "predictions_next_draw": predictions
        },
        "history_summary": history[:20]  # Ultimi 20 concorsi
    }

    with open(DATABASE_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2)

    # Format Telegram HTML Report Supremo
    status_icon = "🟢" if in_range else "🔴"
    pari_cnt = sum(1 for x in sestina if x % 2 == 0)
    dispari_cnt = 6 - pari_cnt

    pred_text = "\n".join([f"🎯 <code>{p}</code>" for p in predictions])

    telegram_msg = (
        f"⚡ <b>VENUS VORTEX — QUANTUM REPORT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Concorso N°:</b> {concorso} ({data_str})\n"
        f"🎲 <b>Sestina:</b> <code>{sestina}</code>\n"
        f"⭐ <b>Jolly:</b> {jolly or '-'} | <b>SuperStar:</b> {star or '-'}\n\n"
        f"📊 <b>METRICHE DI ANALISI:</b>\n"
        f"• <b>Somma Totale:</b> <code>{somma}</code> {status_icon} (Range: 220-320)\n"
        f"• <b>Z-Score Gaussiano:</b> <code>{z_score}</code>\n"
        f"• <b>Entropia di Shannon:</b> <code>{entropy} bits</code>\n"
        f"• <b>Bilanciamento:</b> <code>{pari_cnt} Pari / {dispari_cnt} Dispari</code>\n\n"
        f"🔥 <b>Top 5 Frequenti:</b> {sorted_hot[:5]}\n"
        f"🧊 <b>Top 5 Ritardatari:</b> {sorted_cold[:5]}\n\n"
        f"🔮 <b>PREVISIONI VORTEX (NEXT DRAW):</b>\n"
        f"{pred_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <a href='https://Francis490.github.io/superenalotto-venus-vortex/'><b>Apri Dashboard Live</b></a>"
    )

    send_telegram_alert(telegram_msg)

if __name__ == "__main__":
    main()
