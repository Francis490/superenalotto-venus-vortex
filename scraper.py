import os
import json
import requests
from datetime import datetime

API_ENDPOINT = "https://www.gazzettadellosport.it/api/v1/estrazioni/superenalotto"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Intestazioni per simulare una richiesta da un browser reale (evita il blocco Errno 110)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8',
    'Referer': 'https://www.gazzettadellosport.it/estrazioni/superenalotto'
}

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Credenziali Telegram mancanti nelle variabili d'ambiente.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            print("[TELEGRAM] Notifica inviata con successo.")
        else:
            print(f"[TELEGRAM ERROR] Risposta server Telegram: {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Impossibile inviare il messaggio: {e}")

def fetch_and_sync():
    try:
        print("[CONNECTING] Connessione all'endpoint estrazioni...")
        response = requests.get(API_ENDPOINT, headers=HEADERS, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        latest_draw = data.get('archive', [])[0]
        concorso_num = latest_draw.get("number")
        data_estrazione = latest_draw.get("date")
        sestina = sorted([int(x) for x in latest_draw.get("combination")])
        somma_sestina = sum(sestina)
        jolly = latest_draw.get("jolly")
        star = latest_draw.get("star")

        db_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latest_concorso": concorso_num,
            "latest_sestina": sestina,
            "somma": somma_sestina,
            "in_gaussian_range": 220 <= somma_sestina <= 320,
            "jolly": jolly,
            "superstar": star
        }

        with open("venus_database.json", "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2)

        range_status = "✅ IN RANGE GAUSSIANO (220-320)" if 220 <= somma_sestina <= 320 else "⚠️ FUORI NORMA"

        msg = (
            f"🌀 *VENUS VORTEX DATABASE UPDATED*\n\n"
            f"📌 *Concorso N°:* {concorso_num} del {data_estrazione}\n"
            f"🎲 *Sestina Estratta:* `{sestina}`\n"
            f"📊 *Somma Totale:* `{somma_sestina}` ({range_status})\n"
            f"⭐ *Jolly:* {jolly} | *SuperStar:* {star}\n\n"
            f"⚙️ *Matrice e Modelli Statistici Aggiornati.*"
        )
        
        send_telegram_alert(msg)

    except Exception as e:
        error_msg = f"❌ *VENUS VORTEX SYNC FAILED*\n\nErrore durante la sincronizzazione: `{str(e)}`"
        send_telegram_alert(error_msg)
        raise e

if __name__ == "__main__":
    fetch_and_sync()
