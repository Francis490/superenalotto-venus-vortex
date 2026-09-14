"""
fetch_latest_draw.py
Scarica le ultime estrazioni SuperEnalotto e il jackpot corrente
da fonti pubbliche. Aggiorna venus_history.json e venus_jackpot.json.
Eseguito automaticamente dal workflow prima di scraper.py.
"""
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

HISTORY_FILE = "venus_history.json"
JACKPOT_FILE = "venus_jackpot.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

# ==========================================
# UTILITY
# ==========================================
def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[!] Errore lettura {HISTORY_FILE}: {e}")
        return []

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        print(f"[+] {HISTORY_FILE} salvato ({len(history)} estrazioni).")
    except Exception as e:
        print(f"[!] Errore salvataggio {HISTORY_FILE}: {e}")

def save_jackpot(jackpot_int):
    payload = {
        "jackpot": int(jackpot_int),
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        with open(JACKPOT_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        print(f"[+] {JACKPOT_FILE} salvato: {jackpot_int:,} €")
    except Exception as e:
        print(f"[!] Errore salvataggio {JACKPOT_FILE}: {e}")

def to_int(value, default=None):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def normalize_date(raw):
    if not raw:
        return None
    raw = raw.strip()
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$", raw)
    if m:
        d, mo, y = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if m:
        y, mo, d = m.groups()
        return f"{int(d):02d}/{int(mo):02d}/{y}"
    mesi = {
        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12",
    }
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})$", raw)
    if m:
        d, mese, y = m.groups()
        if mese.lower() in mesi:
            return f"{int(d):02d}/{mesi[mese.lower()]}/{y}"
    return None

def parse_jackpot_text(text):
    """
    Cerca un jackpot tipo '27.300.000' o '27,300,000' o '27300000' nel testo.
    Ritorna un int (importo in euro) o None.
    """
    if not text:
        return None
    # Es: 27.300.000 / 27,300,000 / 27 300 000 / 27300000
    pattern = r"(\d{1,3}(?:[.,\s]\d{3}){1,4}|\d{6,9})"
    matches = re.findall(pattern, text)
    candidates = []
    for m in matches:
        clean = re.sub(r"[.,\s]", "", m)
        try:
            val = int(clean)
        except ValueError:
            continue
        # Filtro di plausibilità: 10M - 400M
        if 10_000_000 <= val <= 400_000_000:
            candidates.append(val)
    if not candidates:
        return None
    # Prendi il più alto (tende a essere il jackpot, non altri numeri)
    return max(candidates)

# ==========================================
# FETCH ESTRAZIONI
# ==========================================
def fetch_draws_from_estrazionedelotto():
    url = "https://www.estrazionedelotto.it/estrazione-superenalotto"
    print(f"[*] Estrazioni fonte 1: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    results = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r"concorso\s*n[°.]?\s*(\d+).*?(\d{2}/\d{2}/\d{4})",
                      line, re.IGNORECASE)
        if m:
            concorso = int(m.group(1))
            data = m.group(2)
            nums, jolly, superstar = [], None, None
            j = i + 1
            while j < len(lines) and len(nums) < 6:
                n = to_int(lines[j])
                if n is not None and 1 <= n <= 90:
                    nums.append(n)
                j += 1
            while j < len(lines) and jolly is None:
                n = to_int(lines[j])
                if n is not None and 1 <= n <= 90:
                    jolly = n
                j += 1
            while j < len(lines) and superstar is None:
                n = to_int(lines[j])
                if n is not None and 1 <= n <= 90:
                    superstar = n
                j += 1
            if len(nums) == 6 and jolly and superstar:
                results.append({
                    "concorso": concorso, "data": data,
                    "combinazione": nums, "jolly": jolly, "superstar": superstar,
                })
            i = j
        else:
            i += 1
    return results

def fetch_draws_from_lottologia():
    url = "https://www.lottologia.com/superenalotto/estrazioni/"
    print(f"[*] Estrazioni fonte 2: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
            if len(cells) < 3:
                continue
            joined = " | ".join(cells)
            m = re.search(r"(\d{4,5})\s*\|.*?(\d{2}[/\-.]\d{2}[/\-.]\d{4})", joined)
            if not m:
                continue
            concorso = int(m.group(1))
            data = normalize_date(m.group(2))
            nums = []
            for c in cells:
                n = to_int(c)
                if n is not None and 1 <= n <= 90:
                    nums.append(n)
            if len(nums) >= 8:
                results.append({
                    "concorso": concorso, "data": data,
                    "combinazione": nums[:6], "jolly": nums[6], "superstar": nums[7],
                })
    return results

def fetch_draws_from_superenalotto_net():
    url = "https://www.superenalotto.net/estrazioni"
    print(f"[*] Estrazioni fonte 3: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    results = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.search(r"(\d{2,4}).*?(\d{2}/\d{2}/\d{4})", line)
        if m:
            concorso = int(m.group(1))
            data = m.group(2)
            nums = []
            j = i + 1
            while j < len(lines) and len(nums) < 8:
                n = to_int(lines[j])
                if n is not None and 1 <= n <= 90:
                    nums.append(n)
                j += 1
            if len(nums) >= 8:
                results.append({
                    "concorso": concorso, "data": data,
                    "combinazione": nums[:6], "jolly": nums[6], "superstar": nums[7],
                })
            i = j
        else:
            i += 1
    return results

def fetch_all_draws():
    candidates = []
    for fn in (fetch_draws_from_estrazionedelotto,
               fetch_draws_from_lottologia,
               fetch_draws_from_superenalotto_net):
        try:
            res = fn()
            print(f"    → {len(res)} estrazioni trovate.")
            if res:
                candidates.append(res)
        except Exception as e:
            print(f"    [!] Errore: {e}")
        time.sleep(1)
    if not candidates:
        return []
    best = max(candidates, key=len)
    seen = set()
    clean = []
    for item in best:
        c = item.get("concorso")
        if c and c not in seen and len(item.get("combinazione", [])) == 6:
            seen.add(c)
            clean.append(item)
    return clean

# ==========================================
# FETCH JACKPOT
# ==========================================
def fetch_jackpot_from_superenalotto_net():
    url = "https://www.superenalotto.net/"
    print(f"[*] Jackpot fonte 1: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Cerca ovunque il termine jackpot e prendi il numero vicino
    for el in soup.find_all(string=re.compile(r"jackpot", re.IGNORECASE)):
        parent_text = el.parent.get_text(" ", strip=True) if el.parent else ""
        val = parse_jackpot_text(parent_text)
        if val:
            return val
    # Fallback: cerca nel testo completo della pagina
    return parse_jackpot_text(soup.get_text(" ", strip=True))

def fetch_jackpot_from_sisal():
    url = "https://www.sisal.it/"
    print(f"[*] Jackpot fonte 2: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    # Cerca sezione con "JACKPOT"
    m = re.search(r"JACKPOT[^\d]{0,40}([\d.,\s]{6,20})", text, re.IGNORECASE)
    if m:
        val = parse_jackpot_text(m.group(1))
        if val:
            return val
    return parse_jackpot_text(text)

def fetch_jackpot_from_estrazionedelotto():
    url = "https://www.estrazionedelotto.it/estrazione-superenalotto"
    print(f"[*] Jackpot fonte 3: {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text(" ", strip=True)
    m = re.search(r"jackpot[^\d]{0,40}([\d.,\s]{6,20})", text, re.IGNORECASE)
    if m:
        val = parse_jackpot_text(m.group(1))
        if val:
            return val
    return parse_jackpot_text(text)

def fetch_all_jackpots():
    for fn in (fetch_jackpot_from_superenalotto_net,
               fetch_jackpot_from_sisal,
               fetch_jackpot_from_estrazionedelotto):
        try:
            val = fn()
            if val:
                print(f"    → Jackpot trovato: {val:,} €")
                return val
        except Exception as e:
            print(f"    [!] Errore: {e}")
        time.sleep(1)
    return None

# ==========================================
# MERGE STORICO
# ==========================================
def merge_history(existing, fetched):
    existing_ids = {item.get("concorso") for item in existing
                    if isinstance(item.get("concorso"), int)}
    max_existing = max(existing_ids) if existing_ids else 0
    new_items = [f for f in fetched
                 if isinstance(f.get("concorso"), int)
                 and f["concorso"] > max_existing]
    if not new_items:
        return existing, 0
    new_items.sort(key=lambda x: x["concorso"])
    for item in new_items:
        item["data"] = normalize_date(item.get("data")) or item.get("data", "N/A")
        item["combinazione"] = [int(n) for n in item["combinazione"]]
        item["jolly"] = to_int(item.get("jolly"))
        item["superstar"] = to_int(item.get("superstar"))
    return existing + new_items, len(new_items)

# ==========================================
# MAIN
# ==========================================
def main():
    print("=== FETCH LATEST DRAW + JACKPOT ===")

    # 1) Estrazioni
    history = load_history()
    print(f"[*] Storico attuale: {len(history)} estrazioni.")
    if history:
        last = history[-1]
        print(f"[*] Ultima: concorso {last.get('concorso')} del {last.get('data')}")

    fetched = fetch_all_draws()
    if fetched:
        print(f"[*] Totale estrazioni recuperate: {len(fetched)}")
        merged, added = merge_history(history, fetched)
        if added > 0:
            save_history(merged)
            print(f"[+] Aggiunte {added} nuove estrazioni. Totale: {len(merged)}")
        else:
            print("[*] Nessuna nuova estrazione. Storico invariato.")
    else:
        print("[!] Nessuna estrazione recuperata.")

    # 2) Jackpot
    print()
    jackpot = fetch_all_jackpots()
    if jackpot:
        save_jackpot(jackpot)
    else:
        print("[!] Impossibile recuperare il jackpot. Verrà usato il DEFAULT.")

if __name__ == "__main__":
    main()
