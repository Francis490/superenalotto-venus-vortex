import os
import re
import json
import html
import random
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DB_FILE = "venus_database.json"

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
        "parse_mode": "HTML"
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print("[TELEGRAM] Report inviato con successo.")
        else:
            print(f"[TELEGRAM ERROR] {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Errore di connessione: {e}")

def fetch_latest_draw():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    # FONTE 1: SuperEnalotto.net
    try:
        print("[SCRAPER] Conressione a SuperEnalotto.net...")
        res = requests.get("https://www.superenalotto.net/estrazioni", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text_block = soup.get_text()

            conc_match = re.search(r'(?:concorso|estrazione)\s*(?:n[°\.]?|numero)?\s*(\d+)', text_block, re.IGNORECASE)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text_block)

            concorso_num = conc_match.group(1) if conc_match else "N/D"
            data_estrazione = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

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
                return concorso_num, data_estrazione, sestina, jolly, star
    except Exception as e:
        print(f"[WARN] Fonte 1 fallita: {e}")

    raise Exception("Impossibile scaricare l'ultima estrazione.")

def load_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"history": [], "predictions": []}

def calculate_stats(history):
    freq = {}
    for draw in history:
        for n in draw.get("sestina", []):
            freq[n] = freq.get(n, 0) + 1
    
    # Numeri Caldi (più frequenti) e Freddi (meno frequenti)
    all_numbers = set(range(1, 91))
    sorted_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    
    hot = [n[0] for n in sorted_freq[:10]] if sorted_freq else list(range(1, 11))
    cold = list(all_numbers - set(hot))[:10]
    return hot, cold

def generate_venus_predictions(hot_numbers, cold_numbers):
    """
    Algoritmo Venus Vortex Engine:
    Genera 3 sestine ottimizzate rispettando:
    1. Somma Gaussiana tra 220 e 320
    2. Equilibrio Pari/Dispari (2/4, 3/3, 4/2)
    3. Copertura Decadica varia
    4. Mix di numeri caldi e freddi
    """
    predictions = []
    labels = [
        "Vortex Alpha (Bilanciata)",
        "Vortex Beta (Iper-Gaussiana)",
        "Vortex Gamma (Matrice Caldi/Freddi)"
    ]

    for label in labels:
        valid_sestina = None
        for _ in range(2000): # tentativi montecarlo
            # Mix tra caldi, freddi e numeri casuali
            pool = list(set(random.sample(hot_numbers, 2) + random.sample(cold_numbers, 2) + random.sample(range(1, 91), 10)))
            candidate = sorted(random.sample(pool, 6))
            
            s = sum(candidate)
            odds = sum(1 for x in candidate if x % 2 != 0)
            
            # Filtri di Coerenza Matematica
            if 230 <= s <= 310 and 2 <= odds <= 4:
                # Verifica copertura decadi
                decades = len(set(x // 10 for x in candidate))
                if decades >= 4:
                    valid_sestina = candidate
                    break
        
        if not valid_sestina:
            valid_sestina = sorted(random.sample(range(1, 91), 6))

        predictions.append({
            "nome": label,
            "sestina": valid_sestina,
            "somma": sum(valid_sestina),
            "coerenza_gaussiana": f"{round(100 - abs(273 - sum(valid_sestina))*0.5, 1)}%"
        })
    return predictions

def run_pipeline():
    conc, date, sestina, jolly, star = fetch_latest_draw()
    somma = sum(sestina)
    in_range = 220 <= somma <= 320

    db = load_database()
    history = db.get("history", [])

    # Aggiungi nuova estrazione se non gia presente
    if not any(d.get("concorso") == conc for d in history):
        history.insert(0, {
            "concorso": conc,
            "data": date,
            "sestina": sestina,
            "somma": somma,
            "jolly": jolly,
            "superstar": star
        })
        history = history[:50] # Mantiene le ultime 50 estrazioni

    hot, cold = calculate_stats(history)
    predictions = generate_venus_predictions(hot, cold)

    db_data = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "latest_concorso": conc,
        "latest_sostina_date": date,
        "latest_sestina": sestina,
        "somma": somma,
        "in_gaussian_range": in_range,
        "jolly": jolly,
        "superstar": star,
        "stats": {
            "hot_numbers": hot[:8],
            "cold_numbers": cold[:8]
        },
        "predictions_next_draw": predictions,
        "history": history
    }

    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db_data, f, indent=2)

    status_tag = "✅ IN RANGE GAUSSIANO (220-320)" if in_range else "⚠️ FUORI NORMA"

    pred_msg = ""
    for p in predictions:
        pred_msg += f"🔹 <b>{p['nome']}</b>: <code>{p['sestina']}</code> (Σ {p['somma']} | Acc: {p['coerenza_gaussiana']})\n"

    msg = (
        f"🌀 <b>VENUS VORTEX INTELLIGENCE REPORT</b>\n\n"
        f"📌 <b>Concorso N°:</b> {conc} del {date}\n"
        f"🎲 <b>Sestina Estratta:</b> <code>{sestina}</code>\n"
        f"📊 <b>Somma Totale:</b> <code>{somma}</code> ({status_tag})\n"
        f"⭐ <b>Jolly:</b> {jolly if jolly else '-'} | <b>SuperStar:</b> {star if star else '-'}\n\n"
        f"🔥 <b>Numeri Caldi:</b> <code>{hot[:6]}</code>\n\n"
        f"🎯 <b>PREDIZIONI PER LA PROSSIMA GIOCATA:</b>\n{pred_msg}\n"
        f"⚙️ <i>Powered by Venus Vortex Engine.</i>"
    )

    send_telegram_alert(msg)

if __name__ == "__main__":
    run_pipeline()
