import os
import json
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8'
}

def send_telegram_alert(html_message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Credenziali Telegram mancanti.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": html_message,
        "parse_mode": "HTML"
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
    sources = [
        "https://www.gazzettadellosport.it/api/v1/estrazioni/superenalotto",
        "https://www.superenalotto.it/api/v1/draws/latest",
        "https://www.sisal.it/api/site/superenalotto/estrazioni/ultimaconcorso"
    ]

    for url in sources:
        try:
            print(f"[CONNECTING] Prova connessione a: {url}")
            res = requests.get(url, headers=HEADERS, timeout=15)
            if res.status_code == 200:
                data = res.json()
                
                # Parsing Gazzetta dello Sport
                if "archive" in data and len(data["archive"]) > 0:
                    latest = data["archive"][0]
                    num = str(latest.get("number", ""))
                    date = latest.get("date", "")
                    sestina = sorted([int(x) for x in latest.get("combination", [])])
                    jolly = latest.get("jolly")
                    star = latest.get("star")
                    return num, date, sestina, jolly, star
                
                # Parsing Superenalotto.it
                elif "combination" in data:
                    num = str(data.get("number", ""))
                    date = data.get("date", "")
                    sestina = sorted([int(x) for x in data.get("combination", [])])
                    jolly = data.get("jolly")
                    star = data.get("star")
                    return num, date, sestina, jolly, star

                # Parsing Sisal
                elif "concorso" in data:
                    c = data.get("concorso", {})
                    e = data.get("estrazione", {})
                    num = str(c.get("numero", ""))
                    date = c.get("dataEstrazione", "")
                    comb = e.get("combinazioneVincenti", []) or e.get("sestina", [])
                    sestina = sorted([int(x) for x in comb[:6]])
                    jolly = e.get("numeroJolly")
                    star = e.get("superStar")
                    return num, date, sestina, jolly, star

        except Exception as err:
            print(f"[WARN] Fonte {url} non raggiungibile: {err}")
            continue

    raise Exception("Tutte le fonti API sono temporaneamente irraggiungibili.")

def fetch_and_sync():
    try:
        concorso_num, data_estrazione, sestina, jolly, star = fetch_latest_draw()
        somma_sestina = sum(sestina)
        in_range = 220 <= somma_sestina <= 320

        db_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "latest_concorso": concorso_num,
            "latest_sestina": sestina,
            "somma": somma_sestina,
            "in_gaussian_range": in_range,
            "jolly": jolly,
            "superstar": star
        }

        with open("venus_database.json", "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2)

        status_tag = "<b>✅ IN RANGE GAUSSIANO (220-320)</b>" if in_range else "<b>⚠️ FUORI NORMA</b>"

        msg = (
            f"🌀 <b>VENUS VORTEX DATABASE UPDATED</b>\n\n"
            f"📌 <b>Concorso N°:</b> {concorso_num} del {data_estrazione}\n"
            f"🎲 <b>Sestina Estratta:</b> <code>{sestina}</code>\n"
            f"📊 <b>Somma Totale:</b> <code>{somma_sestina}</code> ({status_tag})\n"
            f"⭐ <b>Jolly:</b> {jolly} | <b>SuperStar:</b> {star}\n\n"
            f"⚙️ <i>Matrice e Modelli Statistici Aggiornati.</i>"
        )
        
        send_telegram_alert(msg)

    except Exception as e:
        error_msg = f"❌ <b>VENUS VORTEX SYNC FAILED</b>\n\nErrore: <code>{str(e)}</code>"
        send_telegram_alert(error_msg)
        raise e

if __name__ == "__main__":
    fetch_and_sync()
