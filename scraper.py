import os
import re
import json
import html
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(html_message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Credenziali Telegram non configurate nei Secrets.")
        return

    # Pulisce e corregge automaticamente il token da eventuali 'bot' duplicati
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
            print("[TELEGRAM] Notifica inviata con successo.")
        else:
            print(f"[TELEGRAM ERROR] Risposta server Telegram ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Errore invio messaggio: {e}")

def fetch_latest_draw():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    })

    # Fonte 1: Scraping da Estrazioni.it (accessibile da IP cloud)
    try:
        print("[CONNECTING] Tentativo 1: Scraping da estrazioni.it...")
        res = session.get("https://www.estrazioni.it/superenalotto.htm", timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            text = soup.get_text()
            
            match_conc = re.search(r'Concorso\s+n°?\s*(\d+)', text, re.IGNORECASE)
            concorso_num = match_conc.group(1) if match_conc else datetime.now().strftime("%Y%m")
            
            match_date = re.search(r'(\d{2}/\d{2}/\d{4})', text)
            data_estrazione = match_date.group(1) if match_date else datetime.now().strftime("%d/%m/%Y")

            balls = soup.find_all(class_=re.compile(r'(palla|numero|ball)', re.I))
            nums = []
            for b in balls:
                val = b.text.strip()
                if val.isdigit() and 1 <= int(val) <= 90:
                    nums.append(int(val))
            
            if len(nums) >= 6:
                sestina = sorted(nums[:6])
                jolly = nums[6] if len(nums) > 6 else None
                star = nums[7] if len(nums) > 7 else None
                print(f"[SUCCESS] Estrazione trovata: Concorso {concorso_num}, Sestina {sestina}")
                return concorso_num, data_estrazione, sestina, jolly, star
    except Exception as e:
        print(f"[WARN] Fonte 1 fallita: {e}")

    # Fonte 2: Direct API Gazzetta con Sessione
    try:
        print("[CONNECTING] Tentativo 2: Gazzetta dello Sport API...")
        session.headers.update({'Accept': 'application/json, text/plain, */*'})
        res = session.get("https://www.gazzettadellosport.it/api/v1/estrazioni/superenalotto", timeout=15)
        if res.status_code == 200:
            data = res.json()
            if "archive" in data and len(data["archive"]) > 0:
                latest = data["archive"][0]
                num = str(latest.get("number", ""))
                date = latest.get("date", "")
                sestina = sorted([int(x) for x in latest.get("combination", [])])
                jolly = latest.get("jolly")
                star = latest.get("star")
                print(f"[SUCCESS] Estrazione trovata da API Gazzetta: {sestina}")
                return num, date, sestina, jolly, star
    except Exception as e:
        print(f"[WARN] Fonte 2 fallita: {e}")

    raise Exception("Tutte le fonti di estrazione sono temporaneamente non disponibili.")

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
            f"⭐ <b>Jolly:</b> {jolly if jolly is not None else '-'} | <b>SuperStar:</b> {star if star is not None else '-'}\n\n"
            f"⚙️ <i>Matrice e Modelli Statistici Aggiornati.</i>"
        )
        
        send_telegram_alert(msg)

    except Exception as e:
        escaped_err = html.escape(str(e))
        error_msg = f"❌ <b>VENUS VORTEX SYNC FAILED</b>\n\nErrore: <code>{escaped_err}</code>"
        send_telegram_alert(error_msg)
        raise e

if __name__ == "__main__":
    fetch_and_sync()
