import os
import json
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*'
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

def fetch_latest_draw():
    # Endpoints ufficiali Sisal / SuperEnalotto non soggetti a firewall IP
    endpoints = [
        {
            "name": "Sisal Official API",
            "url": "https://www.sisal.it/api/site/superenalotto/estrazioni/ultimaconcorso",
            "type": "sisal"
        },
        {
            "name": "SuperEnalotto Public Endpoint",
            "url": "https://www.superenalotto.it/api/v1/draws/latest",
            "type": "superenalotto"
        }
    ]

    for ep in endpoints:
        try:
            print(f"[CONNECTING] Tentativo di connessione con {ep['name']}...")
            res = requests.get(ep["url"], headers=HEADERS, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if ep["type"] == "sisal":
                    concorso_info = data.get("concorso", {})
                    estrazione_info = data.get("estrazione", {})
                    
                    concorso_num = str(concorso_info.get("numero", ""))
                    data_estrazione = concorso_info.get("dataEstrazione", datetime.now().strftime("%d/%m/%Y"))
                    comb = estrazione_info.get("combinazioneVincenti", []) or estrazione_info.get("sestina", [])
                    sestina = sorted([int(x) for x in comb[:6]])
                    jolly = estrazione_info.get("numeroJolly")
                    star = estrazione_info.get("superStar")
                    return concorso_num, data_estrazione, sestina, jolly, star
                
                elif ep["type"] == "superenalotto":
                    concorso_num = str(data.get("number", ""))
                    data_estrazione = data.get("date", "")
                    sestina = sorted([int(x) for x in data.get("combination", [])])
                    jolly = data.get("jolly")
                    star = data.get("star")
                    return concorso_num, data_estrazione, sestina, jolly, star
        except Exception as e:
            print(f"[WARN] {ep['name']} fallito: {e}")
            continue

    raise Exception("Impossibile contattare i server di estrazione Sisal/SuperEnalotto.")

def fetch_and_sync():
    try:
        concorso_num, data_estrazione, sestina, jolly, star = fetch_latest_draw()
        somma_sestina = sum(sestina)

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
