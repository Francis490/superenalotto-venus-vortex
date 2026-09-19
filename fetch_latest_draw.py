"""
fetch_latest_draw.py
Scarica le ultime estrazioni SuperEnalotto e il jackpot corrente.
Usa proxy intermedi (r.jina.ai, allorigins, corsproxy) per bypassare
i blocchi IP di GitHub Actions verso i siti italiani.

FIX (2026-09-19):
- Parser jackpot riscritto: privilegia numeri vicini alla keyword "jackpot"
  ed esclude il montepremi totale (range ristretto a 10M-200M).
- Import utility condivise da venus_utils.
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
}


# ==========================================
# UTILITY LOCALI
# ==========================================
def load_history():
    """Wrapper che garantisce una lista come ritorno."""
    data = load_json(HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def save_history(history):
    save_json(HISTORY_FILE, history)


def save_jackpot(jackpot_int):
    payload = {
        "jackpot": int(jackpot_int),
        "updated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_json(JACKPOT_FILE, payload)


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


def parse_jackpot_text(text, verbose=False):
    """
    Cerca un importo jackpot plausibile (10M-200M €).

    FIX (2026-09-19):
    - Prima strategia: numeri VICINI alla keyword "jackpot" (contesto).
    - Fallback: numero più alto nel testo che cade nel range.
    - Range ristretto a 10M-200M (esclude montepremi totali, che di solito
      sono più alti del jackpot corrente).
    """
    if not text:
        return None

    # === STRATEGIA 1: contesto "jackpot ... numero" ===
    # Cerca "jackpot" seguito (entro 80 caratteri) da un numero
    pattern_context = r"jackpot[^\d]{0,80}(\d{1,3}(?:[.,\s]\d{3}){1,3}|\d{7,9})"
    matches_context = re.findall(pattern_context, text, re.IGNORECASE)

    candidates_context = []
    for m in matches_context:
        clean = re.sub(r"[.,\s]", "", m)
        try:
            val = int(clean)
        except ValueError:
            continue
        if 10_000_000 <= val <= 200_000_000:
            candidates_context.append(val)

    if verbose:
        print(f"    [debug] Candidati con contesto 'jackpot': {candidates_context}")

    if candidates_context:
        return max(candidates_context)

    # === STRATEGIA 2: fallback generico sul testo ===
    pattern_generic = r"(\d{1,3}(?:[.,\s]\d{3}){1,3}|\d{7,9})"
    matches_generic = re.findall(pattern_generic, text)

    candidates_generic = []
    for m in matches_generic:
        clean = re.sub(r"[.,\s]", "", m)
        try:
            val = int(clean)
        except ValueError:
            continue
        if 10_000_000 <= val <= 200_000_000:
            candidates_generic.append(val)

    if verbose:
        print(f"    [debug] Candidati fallback: {candidates_generic}")

    if not candidates_generic:
        return None
    return max(candidates_generic)


# ==========================================
# FETCH MULTI-PROXY
# ==========================================
def fetch_via_jina(url, timeout=30):
    """r.jina.ai renderizza JS e restituisce markdown pulito."""
    proxy_url = f"https://r.jina.ai/{url}"
    print(f"    → tentativo jina.ai...")
    r = requests.get(proxy_url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, "text"


def fetch_via_allorigins(url, timeout=25):
    proxy_url = f"https://api.allorigins.win/raw?url={url}"
    print(f"    → tentativo allorigins.win...")
    r = requests.get(proxy_url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, "html"


def fetch_via_corsproxy(url, timeout=25):
    proxy_url = f"https://corsproxy.io/?{url}"
    print(f"    → tentativo corsproxy.io...")
    r = requests.get(proxy_url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, "html"


def fetch_via_direct(url, timeout=20):
    print(f"    → tentativo diretto...")
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return r.text, "html"


def smart_fetch(url):
    """
    Prova tutti i metodi in cascata.
    Ritorna (contenuto, tipo) dove tipo è 'html' o 'text'. None se tutto fallisce.
    """
    for fn in (fetch_via_jina, fetch_via_allorigins,
               fetch_via_corsproxy, fetch_via_direct):
        try:
            content, kind = fn(url)
            if content and len(content) > 500:
                print(f"    ✓ successo ({len(content)} byte, {kind})")
                return content, kind
            else:
                print(f"    ✗ risposta troppo corta")
        except Exception as e:
            print(f"    ✗ errore: {e}")
        time.sleep(1)
    return None, None


# ==========================================
# PARSING — Estrazioni
# ==========================================
def parse_draws_from_text(text):
    """
    Parser generico: cerca pattern 'Concorso N. XXX del GG/MM/AAAA'
    seguito da 6 numeri + jolly + superstar.
    """
    results = []
    text = re.sub(r"\s+", " ", text)
    pattern = re.compile(
        r"concorso\s*n[°.]?\s*(\d{2,4})\s*(?:del\s*)?(\d{2}[/\-.]\d{2}[/\-.]\d{4})"
        r"(.{0,400}?)(?=concorso\s*n|$)",
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        concorso = int(m.group(1))
        data = normalize_date(m.group(2))
        chunk = m.group(3)
        nums = [int(n) for n in re.findall(r"\b(\d{1,2})\b", chunk)
                if 1 <= int(n) <= 90]
        seen = set()
        unique_nums = []
        for n in nums:
            if n not in seen:
                seen.add(n)
                unique_nums.append(n)
        if len(unique_nums) >= 8:
            results.append({
                "concorso": concorso,
                "data": data,
                "combinazione": unique_nums[:6],
                "jolly": unique_nums[6],
                "superstar": unique_nums[7],
            })
    return results


def fetch_all_draws():
    """Prova più siti, ritorna la lista più lunga trovata."""
    sources = [
        "https://www.estrazionedelotto.it/estrazione-superenalotto",
        "https://www.superenalotto.net/estrazioni",
        "https://www.lottologia.com/superenalotto/estrazioni/",
    ]
    all_results = []
    for url in sources:
        print(f"[*] Estrazioni da: {url}")
        content, kind = smart_fetch(url)
        if not content:
            print(f"    [!] Fonte non raggiungibile.")
            continue
        if kind == "html":
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ", strip=True)
        else:
            text = content
        draws = parse_draws_from_text(text)
        print(f"    ✓ {len(draws)} estrazioni estratte.")
        if draws:
            all_results.append(draws)
        time.sleep(1)
    if not all_results:
        return []
    best = max(all_results, key=len)
    seen = set()
    clean = []
    for item in sorted(best, key=lambda x: x["concorso"]):
        c = item["concorso"]
        if c not in seen:
            seen.add(c)
            clean.append(item)
    return clean


# ==========================================
# PARSING — Jackpot
# ==========================================
def fetch_jackpot():
    """
    Cerca il jackpot corrente su più siti.

    FIX (2026-09-19):
    - Usa il parser migliorato che privilegia il contesto "jackpot".
    - Log di debug attivo per capire cosa viene scartato.
    """
    sources = [
        "https://www.superenalotto.net/",
        "https://www.estrazionedelotto.it/estrazione-superenalotto",
        "https://www.lottologia.com/superenalotto/",
    ]
    for url in sources:
        print(f"[*] Jackpot da: {url}")
        content, kind = smart_fetch(url)
        if not content:
            continue
        if kind == "html":
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ", strip=True)
        else:
            text = content

        val = parse_jackpot_text(text, verbose=True)
        if val:
            print(f"    ✓ Jackpot trovato: {val:,} €")
            return val

        time.sleep(1)
    return None


# ==========================================
# MERGE
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
    print("=== FETCH LATEST DRAW + JACKPOT (PROXY MODE) ===")

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
    jackpot = fetch_jackpot()
    if jackpot:
        save_jackpot(jackpot)
    else:
        print("[!] Impossibile recuperare il jackpot.")


if __name__ == "__main__":
    main()
