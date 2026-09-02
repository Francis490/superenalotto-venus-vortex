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
        print("[WARN] Credenziali Telegram non configurate.")
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
            print("[TELEGRAM] Notifica inviata con successo.")
        else:
            print(f"[TELEGRAM ERROR] Risposta Telegram ({resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"[TELEGRAM ERROR] Errore invio messaggio: {e}")

def fetch_latest_draw():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en;q=0.8'
    }

    # FONTE 1: SuperEnalotto.net (Static HTML - Accessibile da IP Cloud)
    try:
        print("[CONNECTING] Tentativo 1: SuperEnalotto.net...")
        res = requests.get("https://www.superenalotto.net/estrazioni", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Cerca concorso e data
            text_block = soup.get_text()
            conc_match = re.search(r'Concorso\s*n°?\s*(\d+)', text_block, re.IGNORECASE)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', text_block)

            concorso_num = conc_match.group(1) if conc_match else "N/D"
            data_estrazione = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

            # Cerca i pallini dei numeri estratti
            numbers = []
            for tag in soup.find_all(['li', 'span', 'td']):
                val = tag.text.strip()
                if val.isdigit() and 1 <= int(val) <= 90:
                    # Filtra solo se fa parte della struttura estrazione
                    parent_class = " ".join(tag.get('class', []))
                    if 'ball' in parent_class.lower() or 'numero' in parent_class.lower() or 'sym' in parent_class.lower():
                        numbers.append(int(val))

            # Se i filtri di classe falliscono, cerca per sequenza pura nei tag numerici
            if len(numbers) < 6:
                raw_nums = re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', res.text)
                # Estrai la prima sestina coerente senza duplicati consecutivi
                clean_seq = []
                for n in [int(x) for x in raw_nums]:
                    if len(clean_seq) < 6 and n not in clean_seq:
                        clean_seq.append(n)
                numbers = clean_seq

            if len(numbers) >= 6:
                sestina = sorted(numbers[:6])
                jolly = numbers[6] if len(numbers) > 6 else None
                star = numbers[7] if len(numbers) > 7 else None
                print(f"[SUCCESS] Dati estratti da Fonte 1: Concorso {concorso_num}, Sestina {sestina}")
                return concorso_num, data_estrazione, sestina, jolly, star
    except Exception as e:
        print(f"[WARN] Fonte 1 fallita: {e}")

    # FONTE 2: Agimeg.it (Backup News Outlet)
    try:
        print("[CONNECTING] Tentativo 2: Agimeg.it...")
        res = requests.get("https://www.agimeg.it/estrazioni-superenalotto/", headers=headers, timeout=15)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            page_text = soup.get_text()

            conc_match = re.search(r'concorso\s*numero\s*(\d+)', page_text, re.IGNORECASE)
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', page_text)

            concorso_num = conc_match.group(1) if conc_match else "N/D"
            data_estrazione = date_match.group(1) if date_match else datetime.now().strftime("%d/%m/%Y")

            # Cerca sestina nel testo
            sestina_match = re.search(r'(?:sestina|combinazione|numeri estratti)[^\d]*(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})[,\s\-]+(\d{1,2})', page_text, re.IGNORECASE)
            if sestina_match:
                sestina = sorted([int(sestina_match.group(i)) for i in range(1, 7)])
                print(f"[SUCCESS] Dati estratti da Fonte 2: Sestina {sestina}")
                return concorso_num, data_estrazione, sestina, None, None
    except Exception as e:
        print(f"[WARN] Fonte 2 fallita: {e}")

    raise Exception("Impossibile recuperare l'estrazione dalle fonti disponibili.")

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
