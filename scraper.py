import os
import re
import json
import sys
import urllib.parse
import requests
import numpy as np
import scipy.stats as stats
from itertools import combinations
from bs4 import BeautifulSoup
from datetime import datetime
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

# ==========================================
# 0. TELEGRAM NOTIFIER ENGINE
# ==========================================
def send_telegram_photo(photo_path, caption_html):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    token = TELEGRAM_BOT_TOKEN.strip()
    if token.lower().startswith("bot"): token = token[3:]
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            payload = {"chat_id": TELEGRAM_CHAT_ID.strip(), "caption": caption_html, "parse_mode": "HTML"}
            requests.post(url, data=payload, files={"photo": photo}, timeout=25)
    except Exception:
        pass

# ==========================================
# 1. MOTORE DI ACQUISIZIONE ZENIT (PRECISION V2)
# ==========================================
def validate_zenit_data(data):
    if not data or not isinstance(data, dict): return False
    if "N/A" in [data.get('concorso'), data.get('data'), data.get('jackpot')]: return False
    if not isinstance(data.get('sestina'), list) or len(data.get('sestina')) != 6: return False
    if str(data.get('jackpot', '')).strip() in ["€ 10", "€ 0", "€", ""]: return False
    return True

def fetch_titan_superenalotto():
    targets = [
        "https://www.estrazionedellotto.it/estrazioni-superenalotto",
        "https://www.superenalotto.net/estrazioni"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    months = {
        "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04", 
        "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08", 
        "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
    }

    for target in targets:
        urls_to_try = [
            f"https://api.codetabs.com/v1/proxy?quest={target}",
            f"https://api.allorigins.win/get?url={urllib.parse.quote(target)}",
            target
        ]
        
        for url in urls_to_try:
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code != 200: continue
                
                html = res.json().get("contents", "") if "allorigins" in url else res.text
                if not html or len(html) < 500: continue
                
                soup = BeautifulSoup(html, 'html.parser')
                text = re.sub(r'\s+', ' ', soup.get_text(separator=' ')).strip()

                if "cloudflare" in text.lower(): continue

                result = {
                    "concorso": "N/A",
                    "data": "N/A",
                    "sestina": [],
                    "jolly": "N/A",
                    "superstar": "N/A",
                    "jackpot": "N/A"
                }

                # 1. Estrazione Concorso e Data associata per blocco
                conc_match = re.search(r'Concorso\s*(?:n\.|n|numero)?\s*(\d{1,4})', text, re.I)
                if conc_match:
                    result["concorso"] = conc_match.group(1)

                # Cerca data contestuale vicino alla parola Concorso o nel testo generale
                date_match = re.search(r'\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b', text)
                if date_match:
                    result["data"] = date_match.group(1)
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

# ==========================================
# 2. MOTORE FISICO: USURA AERODINAMICA VENUS
# ==========================================
def calculate_aerodynamic_wear(history):
    """
    Calcola la matrice di usura aerodinamica e meccanica delle palline Venus.
    Integra Sestina (peso 1.0), Jolly (peso 0.5) e SuperStar (peso 0.5)
    applicando un decadimento esponenziale temporale sulle ultime 100 estrazioni.
    """
    wear_matrix = np.zeros(MAX_NUM)
    if not history:
        return wear_matrix

    window_length = min(len(history), 100)
    for idx in range(window_length):
        draw = history[idx]
        impact_weight = np.exp(-0.03 * idx)

        # Usura Sestina
        sestina = draw.get("sestina", [])
        if isinstance(sestina, list):
            for num in sestina:
                try:
                    val = int(num)
                    if 1 <= val <= MAX_NUM:
                        wear_matrix[val - 1] += 1.0 * impact_weight
                except (ValueError, TypeError):
                    continue

        # Usura Jolly
        jolly = draw.get("jolly")
        try:
            if jolly is not None and str(jolly).isdigit():
                val_j = int(jolly)
                if 1 <= val_j <= MAX_NUM:
                    wear_matrix[val_j - 1] += 0.5 * impact_weight
        except (ValueError, TypeError):
            pass

        # Usura SuperStar
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
# 3. MOTORE TITAN: DODECAEDRO & 924 SESTINE
# ==========================================
def generate_titan_matrix(concorso_id, history_data):
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
    gumbel_noise = np.random.gumbel(0, 0.05, size=MAX_NUM)
    adjusted_scores = weights + (aero_wear * 0.35) + gumbel_noise
    
    top_12_indices = np.argsort(adjusted_scores)[-12:] + 1
    dodecaedro = sorted(top_12_indices.tolist())
    
    all_sestine = list(combinations(dodecaedro, 6))
    valid_candidates = []
    
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
        
    if len(valid_candidates) < 4:
        fallback_pool = list(range(1, 91))
        while len(valid_candidates) < 4:
            s = sorted([int(x) for x in np.random.choice(fallback_pool, 6, replace=False)])
            somma = sum(s)
            if 210 <= somma <= 340 and not any(x["sestina"] == s for x in valid_candidates):
                valid_candidates.append({"sestina": s, "somma": somma, "ev_index": 5.0})
                    
    valid_candidates.sort(key=lambda x: (x["ev_index"], -abs(275 - x["somma"])), reverse=True)
    
    selected_titan = []
    for c in valid_candidates:
        if len(selected_titan) == 4: break
        s_set = set(c["sestina"])
        overlap = any(len(s_set.intersection(set(prev["sestina"]))) >= 5 for prev in selected_titan)
        if not overlap: selected_titan.append(c)
            
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
    ax2.set_title('Energia Fisica & Usura Pool 12')
    ax2.invert_yaxis()
    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=200, facecolor=fig.get_facecolor())
    plt.close()

def generate_web_dashboard(se_data, pool_12, matrix):
    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')

    html = f"""<!DOCTYPE html><html lang="it"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>TITAN GOD MODE</title><style>body {{ background: #09090b; color: #f8fafc; font-family: sans-serif; padding: 2rem; }} .container {{ max-width: 900px; margin: 0 auto; background: #18181b; padding: 2rem; border-radius: 12px; }} h1 {{ color: #a855f7; text-align: center; }} .data-box {{ display: flex; justify-content: space-between; background: #27272a; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem; }} .data-item strong {{ font-size: 1.5rem; color: #34d399; }} .pool {{ background: #27272a; padding: 1rem; border-radius: 8px; text-align: center; font-size: 1.2rem; color: #a855f7; margin-bottom: 2rem; border: 1px dashed #a855f7; }} .card {{ background: #09090b; border-left: 5px solid #3b82f6; padding: 1.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; }} .nums {{ font-size: 1.4rem; font-weight: bold; }}</style></head><body><div class="container"><h1>TITAN God Mode Optimal</h1><div class="data-box"><div class="data-item">Concorso<br><strong>N° {conc}</strong></div><div class="data-item">Data<br><strong>{data_est}</strong></div><div class="data-item">Jackpot<br><strong>{jackpot}</strong></div></div><h3 style="color: #a1a1aa;">Ultima Estrazione</h3><div class="pool" style="color: #34d399;">{sestina} | Jolly: {jolly} | SuperStar: {superstar}</div><h3 style="color: #a1a1aa;">Dodecaedro A.I. (Fisica Venus)</h3><div class="pool">{pool_12}</div><h3 style="color: #a1a1aa;">Matrice Ottimizzata (924 Sestine)</h3>"""
    for m in matrix: html += f"""<div class="card"><div><div style="color: #3b82f6; font-size: 0.8rem;">{m['id']}</div><div class="nums">{m['sestina']}</div></div><div style="text-align: right; color: #a1a1aa;">Somma: {m['somma']}<br>EV Score: <strong style="color: #fbbf24;">{m['ev_index']} ⚡</strong></div></div>"""
    html += "</div></body></html>"
    with open(DASHBOARD_FILE, "w", encoding="utf-8") as f: f.write(html)

# ==========================================
# MAIN EXECUTION
# ==========================================
def main():
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: raw_history = json.load(f)
            history = [h for h in raw_history if validate_zenit_data(h)]
        except Exception:
            history = []

    se_data = fetch_titan_superenalotto()
    
    if not se_data:
        if len(history) > 0:
            se_data = history[0]
        else:
            print("Errore critico: Impossibile recuperare dati.")
            sys.exit(1)
            
    if validate_zenit_data(se_data):
        if not any(str(i.get("concorso")) == str(se_data.get("concorso")) for i in history):
            history.insert(0, se_data)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history, f, indent=2)

    concorso_id = se_data.get('concorso', 1)
    pool_12, matrix, physics_scores = generate_titan_matrix(concorso_id, history)
    
    generate_titan_chart(se_data.get("sestina", []), pool_12, physics_scores)
    generate_web_dashboard(se_data, pool_12, matrix)

    conc = se_data.get('concorso', 'N/A')
    data_est = se_data.get('data', 'N/A')
    sestina = se_data.get('sestina', [])
    jolly = se_data.get('jolly', 'N/A')
    superstar = se_data.get('superstar', 'N/A')
    jackpot = se_data.get('jackpot', 'N/A')

    pred_text = "".join([f"🔹 <b>{m['id']}:</b> <code>{m['sestina']}</code>\n   ↳ 📊 Somma: <b>{m['somma']}</b> | ⚡ Anti-Massa: <b>{m['ev_index']}</b>\n" for m in matrix])
    caption = (
        f"👑 <b>TITAN — OPTIMAL MATRIX</b> 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Estrazione:</b> N° {conc} ({data_est})\n"
        f"🎲 <b>Venus:</b> <code>{sestina}</code>\n"
        f"🎯 <b>Jolly:</b> {jolly} | ⭐ <b>SuperStar:</b> {superstar}\n"
        f"💰 <b>Jackpot:</b> <b>{jackpot}</b>\n\n"
        f"🧬 <b>DODECAEDRO A.I. (VENUS WEAR):</b>\n"
        f"<code>{sorted(pool_12)}</code>\n\n"
        f"🔮 <b>SISTEMA TITAN (924 SESTINE FILTRATE):</b>\n{pred_text}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>🌐 Sincronizzazione completata su GitHub Pages.</i>"
    )
    send_telegram_photo(CHART_FILE, caption)

if __name__ == "__main__":
    main()
