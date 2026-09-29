"""
fetch_latest_draw.py
Scarica le ultime estrazioni SuperEnalotto e il jackpot corrente.

VERSIONE DIAGNOSTICA (2026-09-29):
- Logging pesante: per ogni fonte e ogni proxy, salva su file:
  - URL tentato
  - Status HTTP
  - Lunghezza risposta
  - Primi 2000 char della risposta (per capire se HTML è cambiato)
- Al termine, scrive `fetch_debug.log` con tutto lo storico.
- Il log viene committato dal workflow, così possiamo ispezionarlo.
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

# Buffer diagnostico globale (viene scritto su file a fine esecuzione)
DIAG = []


def diag(msg):
    """Aggiunge una riga al buffer diagnostico e la stampa subito."""
    line = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    DIAG.append(line)
    print(line)


def flush_diag():
    """Scrive il buffer diagnostico su file."""
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
    if not text:
        return None

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
        diag(f"    [jackpot] contesto: {candidates_context}")

    if candidates_context:
        return max(candidates_context)

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
        diag(f"    [jackpot] fallback: {candidates_generic}")

    if not candidates_generic:
        return None
    return max(candidates_generic)


# ==========================================
# FETCH MULTI-PROXY (con logging dettagliato)
# ==========================================
def _do_fetch(url, proxy_name, timeout=25):
    """Esegue una richiesta HTTP con logging dettagliato. Ritorna (text, ok)."""
    try:
        diag(f"    → {proxy_name}: GET {url[:100]}...")
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        diag(f"      status={r.status_code} len={len(r.text)} bytes")
        if r.status_code != 200:
            diag(f"      BODY[:500]: {r.text[:500]}")
            return None, False
        return r.text, True
    except requests.Timeout:
        diag(f"      TIMEOUT dopo {timeout}s")
        return None, False
    except requests.ConnectionError as e:
        diag(f"      CONNECTION ERROR: {str(e)[:200]}")
        return None, False
    except Exception as e:
        diag(f"      ERRORE: {type(e).__name__}: {str(e)[:200]}")
        return None, False


def fetch_via_jina(url, timeout=30):
    proxy_url = f"https://r.jina.ai/{url}"
    return _do_fetch(proxy_url, "jina.ai", timeout)


def fetch_via_allorigins(url, timeout=25):
    proxy_url = f"https://api.allorigins.win/raw?url={url}"
    return _do_fetch(proxy_url, "allorigins.win", timeout)


def fetch_via_corsproxy(url, timeout=25):
    proxy_url = f"https://corsproxy.io/?{url}"
    return _do_fetch(proxy_url, "corsproxy.io", timeout)


def fetch_via_direct(url, timeout=20):
    return _do_fetch(url, "diretto", timeout)


def smart_fetch(url):
    """Prova tutti i metodi in cascata. Ritorna (content, kind) o (None, None)."""
    diag(f"[*] smart_fetch: {url}")
    for fn in (fetch_via_jina, fetch_via_allorigins,
               fetch_via_corsproxy, fetch_via_direct):
        content, ok = fn(url)
        if ok and content and len(content) > 500:
            diag(f"    ✓ successo ({len(content)} byte)")
            return content, "html"
        elif ok:
            diag(f"    ✗ risposta troppo corta ({len(content) if content else 0} byte)")
        time.sleep(1)
    diag(f"    ✗ TUTTI I METODI FALLITI per {url}")
    return None, None


# ==========================================
# PARSING — Estrazioni
# ==========================================
def parse_draws_from_text(text):
    """Parser generico: cerca pattern 'Concorso N. XXX del GG/MM/AAAA'."""
    results = []
    text_norm = re.sub(r"\s+", " ", text)

    # Log: cerchiamo le keyword
    kw_count = len(re.findall(r"concorso", text_norm, re.IGNORECASE))
    diag(f"    [parse] occorrenze 'concorso' nel testo: {kw_count}")

    pattern = re.compile(
        r"concorso\s*n[°.]?\s*(\d{2,4})\s*(?:del\s*)?(\d{2}[/\-.]\d{2}[/\-.]\d{4})"
        r"(.{0,400}?)(?=concorso\s*n|$)",
        re.IGNORECASE
    )
    matches = list(pattern.finditer(text_norm))
    diag(f"    [parse] match regex: {len(matches)}")

    for m in matches:
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
            diag(f"    [parse] ✓ concorso {concorso} del {data}: "
                 f"{unique_nums[:6]} | jolly {unique_nums[6]} | ss {unique_nums[7]}")
        else:
            diag(f"    [parse] ✗ concorso {concorso} del {data}: "
                 f"solo {len(unique_nums)} numeri trovati")

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
        diag(f"\n[*] === FONTE: {url} ===")
        content, kind = smart_fetch(url)
        if not content:
            diag(f"    [!] Fonte non raggiungibile.")
            continue

        if kind == "html":
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ", strip=True)
            diag(f"    [html] testo estratto: {len(text)} char")
        else:
            text = content

        # Salva un sample del testo per ispezione
        sample = text[:1500].replace("\n", " ")
        diag(f"    [sample] primi 1500 char: {sample}")

        draws = parse_draws_from_text(text)
        diag(f"    ✓ {len(draws)} estrazioni estratte da questa fonte.")
        if draws:
            all_results.append(draws)
        time.sleep(1)

    if not all_results:
        diag("[!] Nessuna fonte ha restituito estrazioni.")
        return []

    best = max(all_results, key=len)
    diag(f"[+] Fonte migliore: {len(best)} estrazioni")

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
    sources = [
        "https://www.superenalotto.net/",
        "https://www.estrazionedelotto.it/estrazione-superenalotto",
        "https://www.lottologia.com/superenalotto/",
    ]
    for url in sources:
        diag(f"\n[*] === JACKPOT da: {url} ===")
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
            diag(f"    ✓ Jackpot trovato: {val:,} €")
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
    diag("=== FETCH LATEST DRAW + JACKPOT (DIAGNOSTIC MODE) ===")
    diag(f"Python: {sys.version}")
    diag(f"requests: {requests.__version__}")
    diag(f"Now: {datetime.now().isoformat()}")

    try:
        # 1) Estrazioni
        history = load_history()
        diag(f"\n[*] Storico attuale: {len(history)} estrazioni.")
        if history:
            last = history[-1]
            diag(f"[*] Ultima: concorso {last.get('concorso')} del {last.get('data')}")

        fetched = fetch_all_draws()
        if fetched:
            diag(f"\n[*] Totale estrazioni recuperate: {len(fetched)}")
            merged, added = merge_history(history, fetched)
            if added > 0:
                save_history(merged)
                diag(f"[+] Aggiunte {added} nuove estrazioni. Totale: {len(merged)}")
            else:
                diag("[*] Nessuna nuova estrazione. Storico invariato.")
        else:
            diag("[!] Nessuna estrazione recuperata.")

        # 2) Jackpot
        diag("")
        jackpot = fetch_jackpot()
        if jackpot:
            save_jackpot(jackpot)
        else:
            diag("[!] Impossibile recuperare il jackpot.")

    except Exception as e:
        diag(f"[!!!] ECCEZIONE NON GESTITA: {type(e).__name__}: {e}")
        import traceback
        diag(traceback.format_exc())

    finally:
        flush_diag()

    diag("=== FETCH COMPLETATO ===")


if __name__ == "__main__":
    main()
