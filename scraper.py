import os
import re
import json
import sys
import time
import urllib.parse
import requests
import numpy as np
import scipy.stats as stats
from itertools import combinations
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ==========================================
# CONFIGURAZIONE E VARIABILI GLOBALI
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
HISTORY_FILE = "venus_history.json"
DASHBOARD_FILE = "index.html"
CHART_FILE = "vortex_chart.png"
MAX_NUM = 90
NUM_SESTINE = 2  # Focus concentrato su 2 Sestine Ottimali (Titan 1 & Titan 2)
TICKET_COST = 1.0  # Costo giocata singola sestina (€)

MAX_RETRIES = 5        # Numero di tentativi se l'estrazione non è ancora pubblicata
RETRY_DELAY = 180      # Pausa di 3 minuti tra un tentativo e l'altro (in secondi)

# ==========================================
# 0. TELEGRAM NOTIFIER ENGINE
# ==========================================
def send_telegram_photo(photo_path, caption_html):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Token Telegram o Chat ID non configurati. Notifica saltata.")
        return
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"): 
        token = token[3:]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID.strip(), 
                "caption": caption_html, 
                "parse_mode": "HTML"
            }
            res = requests.post(url, data=payload, files={"photo": photo}, timeout=25)
            if res.status_code == 200:
                print("✅ Notifica Telegram inviata con successo.")
            else:
                print(f"❌ Errore invio Telegram ({res.status_code}): {res.text}")
    except Exception as e:
        print(f"❌ Eccezione durante l'invio Telegram: {e}")

# ==========================================
# 1. MOTORE DI ACQUISIZIONE ZENIT (WITH DATE GUARD)
# ==========================================
def is_official_draw_day(date_str):
    """
    Verifica che la data estratta (formato DD/MM/YYYY) corrisponda 
    a un giorno di estrazione ufficiale SuperEnalotto:
    Martedì (1), Giovedì (3), Venerdì (4), Sabato (5).
    """
    try:
        dt = datetime.strptime(date_str, "%d/%m/%Y")
        return dt.weekday() in [1, 3, 4, 5]
    except (ValueError, TypeError):
        return False

def validate_zenit_data(data):
    """
    Valida la struttura e l'anagrafica temporale dei dati estratti.
    """
    if not data or not isinstance(data, dict): 
        return False
    
    date_val = data.get('data', 'N/A')
    if "N/A" in [data.get('concorso'), date_val, data.get('jackpot')]: 
        return False
    
    # GUARDIA CALENDARIO: Scarta i dati se il giorno non è di estrazione ufficiale
    if not is_official_draw_day(date_val):
        print(f"⚠️ [DATE GUARD] Data non valida per estrazione ufficiale: {date_val}")
        return False

    if not isinstance(data.get('sestina'), list) or len(data.get('sestina')) != 6: 
        return False
    if str(data.get('jackpot', '')).strip() in ["€ 10", "€ 0", "€", ""]: 
        return False
    return True

def fetch_single_attempt():
    targets = [
        "https://www.estrazionedellotto.it/estrazioni-superenalotto",
        "https://www.superenalotto.net/estrazioni"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }

    months = {
        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04", 
        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08", 
        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
    }

    timestamp = int(time.time())

    for target in targets:
        target_uncached = f"{target}?_t={timestamp}"
        urls_to_try = [
            f"https://api.codetabs.com/v1/proxy?quest={urllib.parse.quote(target_uncached)}",
            f"https://api.allorigins.win/get?url={urllib.parse.quote(target_uncached)}",
            target_uncached
        ]
        
        for url in urls_to_try:
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code != 200: 
                    continue
                
                html = res.json().get("contents", "") if "allorigins" in url else res.text
                if not html or len(html) < 500: 
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()

                if "cloudflare" in text.lower(): 
                    continue

                result = {
                    "concorso": "N/A",
                    "data": "N/A",
                    "sestina": [],
                    "jolly": "N/A",
                    "superstar": "N/A",
                    "jackpot": "N/A"
                }

                # 1. Estrazione Concorso e Data
                conc_match = re.search(r'Concorso\s*(?:n\.|n|numero)?\s*(\d{1,4})', text, re.I)
                if conc_match:
                    result["concorso"] = conc_match.group(1)

                date_match = re.search(r'\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b', text)
                if date_match:
                    result["data"] = date_match.group(1).replace("-", "/")
                else:
                    date_text_match = re.search(r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})', text, re.I)
                    if date_text_match:
                        d, m_str, y = date_text_match.groups()
                        result["data"] = f"{int(d):02d}/{months[m_str.lower()]}/{y}"

                # 2. Jackpot
                jp_match = re.search(r'(?:Jackpot|Montepremi)[^\d]{1,15}([0-9]{1,3}(?:\.[0-9]{3})*(?:\,[0-9]{2})?)', text, re.I)
                if jp_match and jp_match.group(1) not in ["10", "0"]:
                    result["jackpot"] = f"€ {jp_match.group(1).strip()}"

                # 3. Sestina
                for block in text.split("Concorso"):
                    nums = [int(n) for n in re.findall(r'\b([1-9]|[1-8][0-9]|90)\b', block)]
                    if len(nums) >= 6:
                        valid_nums = list(dict.fromkeys(n for n in nums if 1 <= n <= 90))
                        if len(valid_nums) >= 6:
                            result["sestina"] = sorted(valid_nums[:6])
                            break

                # 4. Jolly
                jolly_match = re.search(r'jolly[^\d]{1,15}(\d{1,2})\b', text, re.I)
                if jolly_match and 1 <= int(jolly_match.group(1)) <= 90:
                    result["jolly"] = int(jolly_match.group(1))

                # 5. SuperStar
                ss_match = re.search(r'superstar[^\d]{1,15}(\d{1,2})\b', text, re.I)
                if ss_match and 1 <= int(ss_match.group(1)) <= 90:
                    result["superstar"] = int(ss_match.group(1))

                if validate_zenit_data(result):
                    return result
                        
            except Exception:
                continue

    return None

def fetch_titan_superenalotto_with_retry(target_date):
    """
    Esegue lo scraping fino a MAX_RETRIES volte finché la data del concorso non coincide con target_date.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"🔄 [TENTATIVO {attempt}/{MAX_RETRIES}] Download dati concorso (Target Date: {target_date})...")
        data = fetch_single_attempt()
        
        if data and data.get("data") == target_date:
            print(f"✅ Estrazione aggiornata trovata per la data di oggi: {target_date} (Concorso N° {data['concorso']})")
            return data
        
        found_date = data.get("data") if data else "Nessun dato"
        print(f"⏳ Concorso del {target_date} non ancora pubblicato (Letti dati per: {found_date}).")
        
        if attempt < MAX_RETRIES:
            print(f"Attesa di {RETRY_DELAY // 60} minuti prima del prossimo tentativo...")
            time.sleep(RETRY_DELAY)

    return None

# ==========================================
# 2. MOTORE FISICO: USURA AERODINAMICA VENUS
# ==========================================
def calculate_aerodynamic_wear(history):
    wear_matrix = np.zeros(MAX_NUM)
    if not history:
        return wear_matrix

    window_length = min(len(history), 100)
    for idx in range(window_length):
        draw = history[idx]
        impact_weight = np.exp(-0.03 * idx)

        sestina = draw.get("sestina", [])
        if isinstance(sestina, list):
            for num in sestina:
                try:
                    val = int(num)
                    if 1 <= val <= MAX_NUM:
                        wear_matrix[val - 1] += 1.0 * impact_weight
                except (ValueError, TypeError):
                    continue

        jolly = draw.get("jolly")
        try:
            if jolly is not None and str(jolly).isdigit():
                val_j = int(jolly)
                if 1 <= val_j <= MAX_NUM:
                    wear_matrix[val_j - 1] += 0.5 * impact_weight
        except (ValueError, TypeError):
            pass

        superstar = draw.get("superstar")
        try:
            if superstar is not None and str(superstar).isdigit():
                val_s = int(superstar)
                if 1 <= val_s <= MAX_NUM:
                    wear_matrix[val_s - 1] += 0.5 * impact_weight
        except (ValueError, TypeError):
            pass

    max_wear = np.max(wear_matrix)
    return wear_matrix / max_wear if max_wear > 0 else wear_matrix

# ==========================================
# 2.B MODULO DEEP SEQUENTIAL (LSTM / MARKOV TRANSITION WEIGHTS)
# ==========================================
def calculate_lstm_sequential_scores(history):
    if len(history) < 5:
        return np.zeros(MAX_NUM)
        
    transition_matrix = np.zeros((MAX_NUM, MAX_NUM))
    
    for i in range(len(history) - 1):
        curr_draw = history[i+1].get("sestina", [])
        next_draw = history[i].get("sestina", [])
        decay = np.exp(-0.02 * i)
        
        for c_num in curr_draw:
            for n_num in next_draw:
                if 1 <= c_num <= MAX_NUM and 1 <= n_num <= MAX_NUM:
                    transition_matrix[c_num - 1, n_num - 1] += decay

    row_sums = transition_matrix.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    transition_probs = transition_matrix / row_sums

    last_sestina = history[0].get("sestina", [])
    lstm_scores = np.zeros(MAX_NUM)
    for num in last_sestina:
        if 1 <= num <= MAX_NUM:
            lstm_scores += transition_probs[num - 1, :]

    max_lstm = np.max(lstm_scores)
    return lstm_scores / max_lstm if max_lstm > 0 else lstm_scores

# ==========================================
# 2.C GESTIONE DEL RISCHIO INTEGRATA (KELLY CRITERION)
# ==========================================
def calculate_kelly_risk_management(jackpot_str, avg_ev_score):
    try:
        clean_jp = re.sub(r'[^\d]', '', jackpot_str.split(',')[0])
        jackpot_val = float(clean_jp) if clean_jp else 100000000.0
    except Exception:
        jackpot_val = 100000000.0

    prob_six = 1.0 / 622614630.0
    ev_booster = max(1.0, float(avg_ev_score) / 5.0)
    expected_payout = jackpot_val * prob_six * ev_booster
    net_ev_per_euro = expected_payout - TICKET_COST
    
    if net_ev_per_euro > 0.1:
        advice_status = "🟢 ELEVATA APPETIBILITÀ"
        risk_level = "OTTIMALE (Jackpot Eccezionale)"
        suggested_play = "Giocare le 2 Sestine TITAN con massima fiducia."
    elif net_ev_per_euro > -0.5:
        advice_status = "🟡 APPETIBILITÀ MEDIA"
        risk_level = "MODERATO (Gestione Budget Consigliata)"
        suggested_play = "Giocare 2 Sestine TITAN (Budget standard 2€)."
    else:
        advice_status = "🟠 PRUDENZA STATISTICA"
        risk_level = "PRUDENTE"
        suggested_play = "Mantenere puntata minima di 2 Sestine TITAN."

    return {
        "jackpot_val": jackpot_val,
        "net_ev_per_euro": round(net_ev_per_euro, 3),
        "advice_status": advice_status,
        "risk_level": risk_level,
        "suggested_play": suggested_play
    }

# ==========================================
# 3. MOTORE TITAN: DODECAEDRO & 2 SESTINE OTTIMALI
# ==========================================
def generate_titan_matrix(concorso_id, history_data, num_sestine_output=NUM_SESTINE):
    try:
        seed_value = 42 + int(str(concorso_id).strip())
    except ValueError:
        seed_value = 42
    np.random.seed(seed_value)
    
    freq = np.zeros(MAX_NUM)
    for draw in history_data:
        for num in draw.get("sestina", []):
            if isinstance(num, int) and 1 <= num <= MAX_NUM:
                freq[num - 1] += 1
                
    weights = freq / (freq.sum() + 1e-6)
    aero_wear = calculate_aerodynamic_wear(history_data)
    lstm_momentum = calculate_lstm_sequential_scores(history_data)
    
    gumbel_noise = np.random.gumbel(0, 0.05, size=MAX_NUM)
    adjusted_scores = weights + (aero_wear * 0.30) + (lstm_momentum * 0.25) + gumbel_noise
    
    top_12_indices = np.argsort(adjusted_scores)[-12:] + 1
    dodecaedro = sorted(top_12_indices.tolist())
    
    all_sestine = list(combinations(dodecaedro, 6))
    valid_candidates = []
    
    # Primo passaggio con filtri rigidi
    for s in all_sestine:
        s = sorted(list(s))
        somma = sum(s)
        
        if not (210 <= somma <= 340): continue
        pari = sum(1 for n in s if n % 2 == 0)
        if not (2 <= pari <= 4): continue
        bassi = sum(1 for n in s if n <= 45)
        if not (2 <= bassi <= 4): continue
            
        consec_flag = False
        for i in range(len(s) - 2):
            if s[i+2] == s[i+1] + 1 == s[i] + 2:
                consec_flag = True
                break
        if consec_flag: continue
            
        score = 100.0
        b_dates = sum(1 for n in s if n <= 31)
        if b_dates > 4: score -= (b_dates - 4) * 15.0
        elif 1 <= b_dates <= 3: score += 5.0
            
        ev = round(min(10.0, max(1.0, score / 10.0)), 2)
        valid_candidates.append({"sestina": s, "somma": somma, "ev_index": ev})
        
    # Fallback di sicurezza
    if not valid_candidates:
        for s in all_sestine:
            s = sorted(list(s))
            somma = sum(s)
            ev = round(min(10.0, max(1.0, 50.0 / 10.0)), 2)
            valid_candidates.append({"sestina": s, "somma": somma, "ev_index": ev})

    valid_candidates.sort(key=lambda x: (x["ev_index"], -abs(273 - x["somma"])), reverse=True)
    
    selected_titan = []
    if valid_candidates:
        titan_1 = valid_candidates[0]
        selected_titan.append(titan_1)
        
        if num_sestine_output > 1:
            t1_set = set(titan_1["sestina"])
            best_t2 = None
            min_overlap = 6
            for cand in valid_candidates[1:]:
                c_set = set(cand["sestina"])
                overlap = len(t1_set.intersection(c_set))
                if overlap <= 2:
                    best_t2 = cand
                    break
                elif overlap < min_overlap:
                    min_overlap = overlap
                    best_t2 = cand
            
            if best_t2 is None and len(valid_candidates) > 1:
                best_t2 = valid_candidates[1]
                
            if best_t2:
                selected_titan.append(best_t2)

    matrix = [{"id": f"TITAN {i}", **item} for i, item in enumerate(selected_titan, 1)]
    return dodecaedro, matrix, adjusted_scores

# ==========================================
# 4. GRAFICA E DASHBOARD
# ==========================================
def generate_titan_chart(sestina, pool_12, physics_scores):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), facecolor='#050505')
    somma = sum(sestina) if sestina else 273
    x = np.linspace(100, 450, 500)
    y = stats.norm.pdf(x, 273.0, 45.5)
    ax1.plot(x, y, color='#d946ef', linewidth=2.5)
    ax1.fill_between(x, y, color='#d946ef', alpha=0.15)
    ax1.axvline(somma, color='#14b8a6', linestyle='--', linewidth=2)
    ax1.set_title(f'Field Area (Somma Ultima Estrazione: {somma})')
    
    scores = [physics_scores[n-1] for n in pool_12]
    ax2.barh([f"N°{n}" for n in pool_12], scores, color='#3b82f6')
    ax2.set_title('Energia Fisica & Deep Momentum Pool 12')
    ax2.invert_yaxis()
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

def generate_web_dashboard(se_data, pool_12, matrix, kelly_info):
    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')

    html = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITAN GOD MODE</title><style>body {{ background: #09090b; color: #f8fafc; font-family: sans-serif; padding: 2rem; }} .container {{ max-width: 900px; margin: 0 auto; background: #18181b; padding: 2rem; border-radius: 12px; }} h1 {{ color: #a855f7; text-align: center; }} .data-box {{ display: flex; justify-content: space-between; background: #27272a; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }} .data-item strong {{ font-size: 1.5rem; color: #34d399; }} .pool {{ background: #27272a; padding: 1rem; border-radius: 8px; text-align: center; font-size: 1.2rem; color: #a855f7; margin-bottom: 2rem; border: 1px dashed #a855f7; }} .risk-box {{ background: #1e1b4b; border: 1px solid #6366f1; padding: 1.2rem; border-radius: 8px; margin-bottom: 2rem; color: #e0e7ff; }} .card {{ background: #09090b; border-left: 5px solid #3b82f6; padding: 1.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }} .nums {{ font-size: 1.4rem; font-weight: bold; }}</style></head><body><div class="container"><h1>TITAN God Mode Optimal (2 Sestine Focused)</h1><div class="data-box"><div class="data-item">Concorso<br><strong>N° {conc}</strong></div><div class="data-item">Data<br><strong>{data_est}</strong></div><div class="data-item">Jackpot<br><strong>{jackpot}</strong></div></div><div class="risk-box"><strong>🛡️ GESTIONE DEL RISCHIO (KELLY MODEL):</strong><br>Stato: {kelly_info['advice_status']}<br>Livello Rischio: {kelly_info['risk_level']}<br>Strategia: {kelly_info['suggested_play']}</div><h3 style="color: #a1a1aa;">Ultima Estrazione</h3><div class="pool" style="color: #34d399;">{sestina} | Jolly: {jolly} | SuperStar: {superstar}</div><h3 style="color: #a1a1aa;">Dodecaedro A.I. (Venus + Deep LSTM)</h3><div class="pool">{pool_12}</div><h3 style="color: #a1a1aa;">2 Sestine Concentrate (Massima Copertura Ortogonale)</h3>"""
    for m in matrix: 
        html += f"""<div class="card"><div><div style="color: #3b82f6; font-size: 0.8rem;">{m['id']}</div><div class="nums">{m['sestina']}</div></div><div style="text-align: right; color: #a1a1aa;">Somma: {m['somma']}<br>EV Score: <strong style="color: #fbbf24;">{m['ev_index']} ⚡</strong></div></div>"""
    html += "</div></body></html>"
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f: 
        f.write(html)

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    now_italy = datetime.now(ZoneInfo("Europe/Rome"))
    today_str = now_italy.strftime("%d/%m/%Y")
    
    print(f"🚀 Avvio TITAN Engine per la data odierna: {today_str}")

    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: 
                raw_history = json.load(f)
            history = [h for h in raw_history if validate_zenit_data(h)]
        except Exception as e:
            print(f"⚠️ Errore lettura {HISTORY_FILE}: {e}")
            history = []

    se_data = fetch_titan_superenalotto_with_retry(today_str)
    
    if not se_data or se_data.get("data") != today_str:
        print(f"⚠️ [ABORT] Nessuna estrazione valida reperita per la data {today_str}.")
        print("Notifica Telegram annullata per evitare l'invio di duplicati vecchi.")
        sys.exit(0)
            
    if validate_zenit_data(se_data):
        if not any(str(i.get("concorso")) == str(se_data.get("concorso")) for i in history):
            history.insert(0, se_data)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: 
                json.dump(history, f, indent=2)

    concorso_id = se_data.get('concorso', 1)
    pool_12, matrix, physics_scores = generate_titan_matrix(concorso_id, history, num_sestine_output=NUM_SESTINE)
    
    avg_ev = np.mean([m['ev_index'] for m in matrix]) if matrix else 5.0
    kelly_info = calculate_kelly_risk_management(se_data.get('jackpot', '€ 100.000.000'), avg_ev)

    generate_titan_chart(se_data.get("sestina", []), pool_12, physics_scores)
    generate_web_dashboard(se_data, pool_12, matrix, kelly_info)

    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')

    pred_text = "".join([f"🔹 <b>{m['id']}:</b> <code>{m['sestina']}</code>\n   ↳ 📊 Somma: <b>{m['somma']}</b> | ⚡ Anti-Massa: <b>{m['ev_index']}</b>\n" for m in matrix])
    caption = (
        f"👑 <b>TITAN V3 — FOCUS 2 SESTINE & RISK MGMT</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Estrazione:</b> N° {conc} ({data_est})\n"
        f"🎲 <b>Venus:</b> <code>{sestina}</code>\n"
        f"🎯 <b>Jolly:</b> {jolly} | ⭐ <b>SuperStar:</b> {superstar}\n"
        f"💰 <b>Jackpot:</b> <b>{jackpot}</b>\n\n"
        f"🧬 <b>DODECAEDRO A.I. (VENUS WEAR + LSTM):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>2 SESTINE OTTIMALI CONCENTRATE:</b>\n{pred_text}\n"
        f"🛡️ <b>RISK MANAGEMENT (KELLY MODEL):</b>\n"
        f"• Status: <b>{kelly_info['advice_status']}</b>\n"
        f"• Consiglio: <i>{kelly_info['suggested_play']}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🌐 Sincronizzazione completata su GitHub Pages.</i>"
    )
    
    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
if __name__ == "__main__":
    main()
