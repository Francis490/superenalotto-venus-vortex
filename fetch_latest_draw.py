"""
fetch_latest_draw.py
VENUS VORTEX — Recupero estrazioni SuperEnalotto.

RISCRITTURA (2026-10-05):
- Rimossi proxy morti (jina.ai 403, allorigins 522, corsproxy 403).
- Uso esclusivo di lottologia.com (unica fonte stabile).
- Parser specifico per formato "NNN/YY - weekday DD mese YYYY".
- Retry con backoff esponenziale (3 tentativi).
- Fail esplicito (exit 1) se nessun draw recuperato.
- Rimosso completamente il fetch del jackpot (dato gestito via override manuale).

Uso:
    python fetch_latest_draw.py
"""
import json
import os
import re
import sys
import time
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

# ==========================================
# FONTE
# ==========================================
DRAWS_URL = "https://www.lottologia.com/superenalotto/estrazioni/"

# Retry policy
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 45]  # secondi

# Mesi italiani
MESI_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4,
    "maggio": 5, "giugno": 6, "luglio": 7, "agosto": 8,
    "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

# Buffer diagnostico
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
    return None


def parse_italian_date(day, month_name, year):
    """
    Converte (2, 'ottobre', '2026') -> '02/10/2026'.
    Ritorna None se mese non riconosciuto.
    """
    month_key = month_name.strip().lower()
    if month_key not in MESI_IT:
        return None
    try:
        d = int(day)
        y = int(year)
    except (ValueError, TypeError):
        return None
    if not (1 <= d <= 31 and 2000 <= y <= 2100):
        return None
    return f"{d:02d}/{MESI_IT[month_key]:02d}/{y}"


# ==========================================
# HTTP CON RETRY
# ==========================================
def fetch_with_retry(url, timeout=30):
    """
    Fetch con retry esponenziale.
    Ritorna testo HTML o None se tutti i tentativi falliscono.
    """
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
# PARSING — Estrazioni
# ==========================================
def parse_draws_from_text(text):
    """
    Parser per lottologia.com.

    Formato osservato:
        "158/26 - venerdì 2 ottobre 2026"
        seguito dai numeri (6 + jolly + superstar)

    Strategia:
    1. Trova tutti i marker "NNN/YY - weekday DD mese YYYY"
    2. Per ciascuno, prende i ~600 char successivi
    3. Estrae i primi 8 numeri 1-90 distinti (6 + jolly + superstar)
    """
    results = []
    text_norm = re.sub(r"\s+", " ", text)

    marker_pattern = re.compile(
        r"(\d{2,4})/(\d{2})\s*-\s*"
        r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\s+"
        r"(\d{1,2})\s+"
        r"(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+"
        r"(\d{4})",
        re.IGNORECASE
    )

    matches = list(marker_pattern.finditer(text_norm))
    diag(f"    [parse] marker trovati: {len(matches)}")

    for i, m in enumerate(matches):
        concorso_raw = m.group(1)
        day = m.group(3)
        month_name = m.group(4)
        year = m.group(5)

        concorso = to_int(concorso_raw)
        if concorso is None:
            continue

        data_str = parse_italian_date(day, month_name, year)
        if data_str is None:
            diag(f"    [parse] data non parsabile: {day} {month_name} {year}")
            continue

        start = m.end()
        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = min(start + 600, len(text_norm))

        chunk = text_norm[start:end]

        raw_nums = re.findall(r"\b(\d{1,2})\b", chunk)
        nums = []
        seen = set()
        for ns in raw_nums:
            n = to_int(ns)
            if n is None:
                continue
            if not (1 <= n <= 90):
                continue
            if n in seen:
                continue
            seen.add(n)
            nums.append(n)
            if len(nums) == 8:
                break

        if len(nums) < 8:
            diag(f"    [parse] concorso {concorso} ({data_str}): "
                 f"solo {len(nums)} numeri trovati, scarto")
            continue

        results.append({
            "concorso": concorso,
            "data": data_str,
            "combinazione": nums[:6],
            "jolly": nums[6],
            "superstar": nums[7],
            "sestina": nums[:6],
        })
        diag(f"    [parse] ✓ concorso {concorso} ({data_str}): "
             f"{nums[:6]} | J {nums[6]} | SS {nums[7]}")

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
    diag(f"    [html] sample: {text[:300]}...")

    draws = parse_draws_from_text(text)
    diag(f"    [+] {len(draws)} estrazioni estratte")

    if not draws:
        return []

    seen = set()
    clean = []
    for d in sorted(draws, key=lambda x: x["concorso"]):
        if d["concorso"] in seen:
            continue
        seen.add(d["concorso"])
        clean.append(d)

    return clean


# ==========================================
# MERGE
# ==========================================
def merge_history(existing, fetched):
    existing_ids = {item.get("concorso") for item in existing
                    if isinstance(item.get("concorso"), int)}

    new_items = [f for f in fetched
                 if isinstance(f.get("concorso"), int)
                 and f["concorso"] not in existing_ids]

    if not new_items:
        return existing, 0

    new_items.sort(key=lambda x: x["concorso"])

    for item in new_items:
        item["data"] = normalize_date(item.get("data")) or item.get("data", "N/A")
        item["combinazione"] = [int(n) for n in item["combinazione"]]
        item["sestina"] = item["combinazione"]
        item["jolly"] = to_int(item.get("jolly"))
        item["superstar"] = to_int(item.get("superstar"))

    merged = existing + new_items

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
