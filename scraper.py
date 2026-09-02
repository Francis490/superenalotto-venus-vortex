import os
import json
import urllib.request
import urllib.parse
from datetime import datetime

API_ENDPOINT = "https://www.gazzettadellosport.it/api/v1/estrazioni/superenalotto"

def send_telegram_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("[WARN] Credenziali Telegram mancanti nelle variabili d'ambiente.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req) as response:
            print("[TELEGRAM] Notifica inviata con successo.")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Impossibile inviare il messaggio: {e}")

def fetch_and_sync():
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(API_ENDPOINT, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            
            latest_draw = data.get('archive', [])[0]
            concorso_num = latest_draw.get("number")
            data_estrazione = latest_draw.get("date")
            sestina = sorted([int(x) for x in latest_draw.get("combination")])
            somma_sestina = sum(sestina)
            jolly = latest_draw.get("jolly")
            star = latest_draw.get("star")

            # Strutturazione database
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

            # Messaggio Telegram
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
