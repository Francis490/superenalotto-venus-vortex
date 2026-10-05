"""
fetch_latest_draw.py
VENUS VORTEX — Recupero estrazioni SuperEnalotto.

RISCRITTURA (2026-10-05 v3):
- Parser riscritto per il formato REALE di lottologia.com:
    "3 Ott 2026 Numeri 05 12 18 25 28 42 jolly 66 superstar 76"
  (il formato "158/26 - venerdì 2 ottobre" non esiste!)
- Assegnazione automatica del concorso:
  confronto con la history esistente; i concorsi nuovi ricevono
  max_concorso + 1, +2, ... in ordine cronologico.
- Normalizzazione Unicode NFC.
- Fetch da lottologia.com (unico che risponde 200).

Uso:
    python fetch_latest_draw.py
"""
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from venus_utils import load_json, save_json


HISTORY_FILE = "venus_history.json"
DEBUG_LOG_FILE = "fetch_debug.log"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

DRAWS_URL = "https://www.lottologia.com/superenalotto/estrazioni/"

MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]

# Mesi abbreviati italiani (formato lottologia)
MESI_ABBR = {
    "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6,
    "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12,
}

DIAG = []


def diag(msg):
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    DIAG.append(line)
    print(line)


def flush_diag():
    try:
        with open(DEBUG_LOG_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(DIAG))
        print(f"[+] Diagnostica salvata in {DEBUG_LOG_FILE} ({len(DIAG)} righe)")
    except Exception as e:
        print(f"[!] Errore salvataggio diagnostica: {e}")


# ==========================================
# UTILITY
# ==========================================
def load_history():
    data = load_json(HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def save_history(history):
    save_json(HISTORY_FILE, history)


def to_int(value, default=None):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def fetch_with_retry(url, timeout=30):
    diag(f"[*] Fetch: {url}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            diag(f"    → tentativo {attempt}/{MAX_RETRIES}")
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            diag(f"      status={r.status_code} len={len(r.text)} bytes")

            if r.status_code == 200 and len(r.text) > 1000:
                diag(f"      ✓ successo")
                return r.text

            diag(f"      ✗ status/len non validi")

        except requests.Timeout:
            diag(f"      ✗ TIMEOUT dopo {timeout}s")
        except requests.ConnectionError as e:
            diag(f"      ✗ CONNECTION ERROR: {str(e)[:150]}")
        except Exception as e:
            diag(f"      ✗ ERRORE: {type(e).__name__}: {str(e)[:150]}")

        if attempt < MAX_RETRIES:
            delay = RETRY_DELAYS[attempt - 1]
            diag(f"      → attendo {delay}s prima del prossimo tentativo")
            time.sleep(delay)

    diag(f"[!] Tutti i tentativi falliti per {url}")
    return None


# ==========================================
# PARSING — Estrazioni (formato lottologia)
# ==========================================
def parse_draws_from_text(text):
    """
    Parser per il formato REALE di lottologia.com:

        "3 Ott 2026 Numeri 05 12 18 25 28 42 jolly 66 superstar 76"

    Nessun numero di concorso accanto all'estrazione. Il concorso verrà
    assegnato in fase di merge, basandosi sulla history esistente.
    """
    # Normalizzazione Unicode (evita problemi con accenti composti/decomposti)
    text = unicodedata.normalize("NFC", text)
    text_norm = re.sub(r"\s+", " ", text)

    # Pattern per il formato reale
    pattern = re.compile(
        r"(\d{1,2})\s+"                                             # giorno
        r"(gen|feb|mar|apr|mag|giu|lug|ago|set|ott|nov|dic)\s+"     # mese
        r"(\d{4})\s+"                                               # anno
        r"[Nn]umeri\s+"                                             # keyword
        r"((?:\d{1,2}\s+){5}\d{1,2})\s+"                            # 6 numeri
        r"jolly\s+(\d{1,2})\s+"                                     # jolly
        r"superstar\s+(\d{1,2})",                                   # superstar
        re.IGNORECASE
    )

    matches = list(pattern.finditer(text_norm))
    diag(f"    [parse] marker trovati: {len(matches)}")

    results = []
    for m in matches:
        day = int(m.group(1))
        month_abbr = m.group(2).lower()
        year = int(m.group(3))
        nums_str = m.group(4)
        jolly = int(m.group(5))
        superstar = int(m.group(6))

        month = MESI_ABBR.get(month_abbr)
        if not month:
            continue

        nums = [int(n) for n in re.findall(r"\d{1,2}", nums_str)]
        if len(nums) != 6:
            continue

        # Validazione: numeri distinti 1-90
        if len(set(nums)) != 6 or not all(1 <= n <= 90 for n in nums):
            continue

        data_str = f"{day:02d}/{month:02d}/{year}"

        results.append({
            "data": data_str,
            "combinazione": nums,
            "jolly": jolly,
            "superstar": superstar,
            "sestina": nums,
            "concorso": None,  # Assegnato dopo
        })

    # Ordina per data crescente (le estrazioni del sito sono decrescenti)
    results.sort(key=lambda x: (
        int(x["data"][-4:]),  # anno
        int(x["data"][3:5]),  # mese
        int(x["data"][:2]),   # giorno
    ))

    return results


def fetch_all_draws():
    diag(f"\n[*] === ESTRAZIONI da {DRAWS_URL} ===")
    html = fetch_with_retry(DRAWS_URL)
    if not html:
        diag(f"[!] Impossibile recuperare estrazioni.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    diag(f"    [html] testo estratto: {len(text)} char")

    draws = parse_draws_from_text(text)
    diag(f"    [+] {len(draws)} estrazioni estratte")

    if draws:
        # Log delle prime 3 e ultime 3
        for d in draws[-3:]:
            diag(f"    [parse] recente: {d['data']} -> {d['combinazione']} "
                 f"J {d['jolly']} SS {d['superstar']}")

    return draws


# ==========================================
# MERGE + ASSEGNAZIONE CONCORSI
# ==========================================
def merge_history(existing, fetched):
    """
    Aggiunge estrazioni nuove. Assegna i concorsi mancanti
    in base alla history esistente.

    Logica concorsi:
    1. Costruisci mappa data → concorso dalla history esistente
    2. Per ogni nuova estrazione (data non in history), assegna
       max_concorso + 1 (per il suo anno), in ordine cronologico
    3. Se la nuova estrazione è dello stesso anno di altre,
       il numero cresce progressivamente
    """
    # Mappa date esistenti
    date_to_concorso = {}
    for d in existing:
        data = d.get("data", "")
        if data and isinstance(d.get("concorso"), int):
            date_to_concorso[data] = d["concorso"]

    # Concorso massimo per ogni anno
    max_concorso_by_year = {}
    for d in existing:
        data = d.get("data", "")
        c = d.get("concorso")
        if len(data) >= 4 and isinstance(c, int):
            year = data[-4:]
            max_concorso_by_year[year] = max(
                max_concorso_by_year.get(year, 0), c
            )

    # Filtra: tieni solo estrazioni con data NON già presente
    new_items = []
    for item in fetched:
        data = item.get("data", "")
        if not data:
            continue
        if data in date_to_concorso:
            continue
        new_items.append(item)

    if not new_items:
        return existing, 0

    # Ordina i nuovi per data crescente (già fatto in parse, ma per sicurezza)
    new_items.sort(key=lambda x: (
        int(x["data"][-4:]),
        int(x["data"][3:5]),
        int(x["data"][:2]),
    ))

    # Assegna concorsi in sequenza
    for item in new_items:
        year = item["data"][-4:]
        next_c = max_concorso_by_year.get(year, 0) + 1
        item["concorso"] = next_c
        max_concorso_by_year[year] = next_c

    # Merge
    merged = existing + new_items

    # Sort cronologico
    def sort_key(x):
        try:
            dt = datetime.strptime(x.get("data", ""), "%d/%m/%Y")
            return (dt.year, dt.month, dt.day)
        except Exception:
            return (0, 0, 0)

    merged = sorted(merged, key=sort_key)
    return merged, len(new_items)


# ==========================================
# MAIN
# ==========================================
def main():
    diag("=== FETCH LATEST DRAW ===")
    diag(f"Python: {sys.version}")
    diag(f"requests: {requests.__version__}")
    diag(f"Now: {datetime.now().isoformat()}")

    exit_code = 0

    try:
        history = load_history()
        diag(f"\n[*] Storico attuale: {len(history)} estrazioni.")
        if history:
            last = history[-1]
            diag(f"[*] Ultima entry: concorso {last.get('concorso')} "
                 f"del {last.get('data')}")

        fetched = fetch_all_draws()

        if fetched:
            diag(f"\n[*] Totale estrazioni recuperate: {len(fetched)}")
            merged, added = merge_history(history, fetched)
            if added > 0:
                save_history(merged)
                diag(f"[+] Aggiunte {added} nuove estrazioni. "
                     f"Totale: {len(merged)}")
                # Log delle aggiunte
                for item in merged[-added:]:
                    diag(f"    + concorso {item['concorso']} ({item['data']}): "
                         f"{item['combinazione']}")
            else:
                diag("[*] Nessuna nuova estrazione. Storico invariato.")
        else:
            diag("[!!!] NESSUNA ESTRAZIONE RECUPERATA.")
            exit_code = 1

    except Exception as e:
        diag(f"[!!!] ECCEZIONE: {type(e).__name__}: {e}")
        import traceback
        diag(traceback.format_exc())
        exit_code = 1

    diag("=== FETCH COMPLETATO ===")
    flush_diag()

    if exit_code != 0:
        print(f"\n[!!!] Fetch terminato con errori (exit code {exit_code})")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
