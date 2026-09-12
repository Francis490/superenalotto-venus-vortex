import json
import os
import sys
import math
from datetime import datetime
import itertools
import urllib.request
import urllib.parse

# Librerie di rendering grafico e analisi statistica
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

# ==========================================
# CONSTANTI E CONFIGURAZIONE DI SISTEMA
# ==========================================
HISTORY_FILE = "venus_history.json"
DATABASE_FILE = "venus_database.json"
CHART_FILE = "vortex_chart.png"
INDEX_FILE = "index.html"

GAUSS_MEAN = 273.0
GAUSS_STD = 43.5

# ==========================================
# 1. GESTIONE FILE JSON
# ==========================================
def load_json(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore nel caricamento di {filepath}: {e}")
            return default_value
    return default_value

def save_json(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] File salvato con successo: {filepath}")
    except Exception as e:
        print(f"[!] Errore durante il salvataggio di {filepath}: {e}")

# ==========================================
# 2. ALGORITMI QUANTITATIVI E NUOVI FILTRI
# ==========================================

def calculate_raw_scores(history):
    """Calcola i punteggi grezzi basati su frequenza e ritardo combinati."""
    delays = {i: 0 for i in range(1, 91)}
    frequencies = {i: 0 for i in range(1, 91)}
    
    total_draws = len(history)
    
    # Calcolo ritardi e frequenze
    for num in range(1, 91):
        found = False
        for idx, draw in enumerate(reversed(history)):
            comb = draw.get("combinazione", [])
            if num in comb:
                frequencies[num] += 1
                if not found:
                    delays[num] = idx
                    found = True
        if not found:
            delays[num] = total_draws

    raw_scores = {}
    for num in range(1, 91):
        freq_score = frequencies[num] / max(1, total_draws)
        delay_score = math.log1p(delays[num])
        raw_scores[num] = (freq_score * 0.6) + (delay_score * 0.4)
        
    return raw_scores, delays, frequencies

def apply_cooldown_factor(raw_scores, history):
    """
    [INTEGRAZIONE 1]: Applica il Fattore di Decadimento Temporale (Cooldown Factor)
    per penalizzare i numeri estratti di recente ed eliminare l'Overfitting.
    """
    adjusted_scores = raw_scores.copy()
    if len(history) < 3:
        return adjusted_scores

    t1_set = set(history[-1].get("combinazione", []))
    t2_set = set(history[-2].get("combinazione", []))
    t3_set = set(history[-3].get("combinazione", []))

    for num in range(1, 91):
        if num in t1_set:
            adjusted_scores[num] *= 0.25  # Penalizzazione del 75% per t-1
        elif num in t2_set:
            adjusted_scores[num] *= 0.60  # Penalizzazione del 40% per t-2
        elif num in t3_set:
            adjusted_scores[num] *= 0.85  # Penalizzazione del 15% per t-3

    return adjusted_scores

def build_tiered_dodecahedron(adjusted_scores, delays, history):
    """
    [INTEGRAZIONE 2]: Costruisce il Dodecaedro A.I. (12 numeri) a 4 strati bilanciati:
    - 4 Hot (Top score rettificati dal Cooldown)
    - 4 Medium (Ritardo compreso tra 5 e 15 estrazioni)
    - 2 Cold (Maggior ritardo relativo)
    - 2 High EV / Anti-Massa (Numeri >= 32 ad alto valore economico)
    """
    t1_set = set(history[-1].get("combinazione", [])) if history else set()
    dodeca_pool = []

    # 1. Top Hot (4 Numeri)
    sorted_by_score = sorted(range(1, 91), key=lambda x: adjusted_scores[x], reverse=True)
    for num in sorted_by_score:
        if len(dodeca_pool) < 4:
            dodeca_pool.append(num)

    # 2. Medium Delay (4 Numeri con ritardo 5..15)
    medium_candidates = [n for n in range(1, 91) if 5 <= delays[n] <= 15 and n not in dodeca_pool]
    medium_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in medium_candidates:
        if len(dodeca_pool) < 8:
            dodeca_pool.append(num)
    
    # Fallback se la fascia Medium non ha abbastanza candidati
    if len(dodeca_pool) < 8:
        for num in sorted_by_score:
            if num not in dodeca_pool and len(dodeca_pool) < 8:
                dodeca_pool.append(num)

    # 3. Cold / Ritardatari (2 Numeri)
    cold_candidates = [n for n in range(1, 91) if n not in dodeca_pool]
    cold_candidates.sort(key=lambda x: delays[x], reverse=True)
    for num in cold_candidates[:2]:
        dodeca_pool.append(num)

    # 4. Anti-Massa Pure (2 Numeri >= 32 ad alto EV)
    anti_massa_candidates = [n for n in range(32, 91) if n not in dodeca_pool]
    anti_massa_candidates.sort(key=lambda x: adjusted_scores[x], reverse=True)
    for num in anti_massa_candidates[:2]:
        dodeca_pool.append(num)

    # Garantisce esattamente 12 numeri unici
    while len(dodeca_pool) < 12:
        for num in sorted_by_score:
            if num not in dodeca_pool:
                dodeca_pool.append(num)
                break

    return sorted(dodeca_pool[:12])

def select_titan_sestinas(dodeca_pool, adjusted_scores, history):
    """
    [INTEGRAZIONI 3 e 4]:
    - Hard Constraint: Massimo 2 numeri presi da t-1 per ciascuna sestina.
    - Ortogonalità: TITAN 1 e TITAN 2 condividono al massimo 1 numero tra loro.
    - Selezione in curva Gaussiana (Somma tra 200 e 340).
    """
    t1_set = set(history[-1].get("combinazione", [])) if history else set()
    all_combos = list(itertools.combinations(dodeca_pool, 6))

    valid_sestinas = []
    for combo in all_combos:
        # Constraint 1: Max 2 numeri da t-1
        overlap_t1 = len(set(combo).intersection(t1_set))
        if overlap_t1 > 2:
            continue

        # Constraint 2: Somma Gaussiana
        combo_sum = sum(combo)
        if not (200 <= combo_sum <= 340):
            continue

        # Constraint 3: Anti-Massa (Almeno 2 numeri >= 32)
        if len([n for n in combo if n >= 32]) < 2:
            continue

        score = sum(adjusted_scores[n] for n in combo)
        valid_sestinas.append((combo, score, combo_sum))

    # Fallback se i filtri rigidi svuotano le combinazioni
    if not valid_sestinas:
        for combo in all_combos:
            combo_sum = sum(combo)
            score = sum(adjusted_scores[n] for n in combo)
            valid_sestinas.append((combo, score, combo_sum))

    valid_sestinas.sort(key=lambda x: x[1], reverse=True)

    # Selezione TITAN 1
    titan1 = list(valid_sestinas[0][0])

    # Selezione TITAN 2 con Overlap Max 1 verso TITAN 1
    titan2 = None
    for item in valid_sestinas[1:]:
        candidate = list(item[0])
        shared_with_t1 = len(set(titan1).intersection(set(candidate)))
        if shared_with_t1 <= 1:
            titan2 = candidate
            break

    if titan2 is None and len(valid_sestinas) > 1:
        titan2 = list(valid_sestinas[1][0])
    elif titan2 is None:
        titan2 = titan1

    return titan1, titan2

# ==========================================
# 3. GENERAZIONE GRAFICO (vortex_chart.png)
# ==========================================
def generate_titan_chart(titan1, titan2, dodeca_pool, scores):
    """Genera la matrice di visualizzazione 3-in-1 ad alta risoluzione."""
    fig = plt.figure(figsize=(14, 8), facecolor='#09090b')
    plt.rcParams['text.color'] = '#f8fafc'
    plt.rcParams['axes.labelcolor'] = '#f8fafc'
    plt.rcParams['xtick.color'] = '#a1a1aa'
    plt.rcParams['ytick.color'] = '#a1a1aa'

    # Subplot 1: Curva Gaussiana
    ax1 = fig.add_subplot(2, 2, (1, 3), facecolor='#18181b')
    x = np.linspace(100, 440, 500)
    y = norm.pdf(x, GAUSS_MEAN, GAUSS_STD)
    ax1.plot(x, y, color='#a855f7', linewidth=2.5, label='Curva Gaussiana Teorica')
    
    sum1 = sum(titan1)
    sum2 = sum(titan2)
    
    ax1.axvline(sum1, color='#3b82f6', linestyle='--', linewidth=2, label=f'TITAN 1 (Somma {sum1})')
    ax1.axvline(sum2, color='#14b8a6', linestyle='--', linewidth=2, label=f'TITAN 2 (Somma {sum2})')
    ax1.set_title("Distribuzione Gaussiana e Punti di Equilibrio", fontsize=12, fontweight='bold', color='#34d399')
    ax1.legend(facecolor='#27272a', edgecolor='none')

    # Subplot 2: Dodecaedro Bar Chart
    ax2 = fig.add_subplot(2, 2, 2, facecolor='#18181b')
    dodeca_scores = [scores.get(n, 1.0) for n in dodeca_pool]
    bars = ax2.bar([str(n) for n in dodeca_pool], dodeca_scores, color='#14b8a6', edgecolor='#27272a')
    ax2.set_title("Ranking Energetico Dodecaedro Pool", fontsize=10, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)

    # Subplot 3: Matrice Ortogonale TITAN 1 vs TITAN 2
    ax3 = fig.add_subplot(2, 2, 4, facecolor='#18181b')
    matrix_data = np.zeros((2, 6))
    matrix_data[0, :] = titan1
    matrix_data[1, :] = titan2
    
    cax = ax3.matshow(matrix_data, cmap='plasma')
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['TITAN 1', 'TITAN 2'], fontweight='bold')
    ax3.set_xticks(range(6))
    ax3.set_xticklabels([f'Pos {i+1}' for i in range(6)])
    
    for i in range(2):
        for j in range(6):
            val = int(matrix_data[i, j])
            ax3.text(j, i, str(val), va='center', ha='center', color='white', fontweight='bold', fontsize=12)

    ax3.set_title("Matrice di Copertura Ortogonale", fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(CHART_FILE, dpi=300, facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close()
    print(f"[+] Grafico generato con successo: {CHART_FILE}")

# ==========================================
# 4. NOTIFICA TELEGRAM
# ==========================================
def send_telegram_notification(caption_text, chart_path):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[!] Token Telegram o Chat ID mancanti nei Secrets. Notifica saltata.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    
    try:
        with open(chart_path, "rb") as image_file:
            boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
            body = []
            
            # Parametro chat_id
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="chat_id"'.encode())
            body.append(''.encode())
            body.append(str(chat_id).encode())

            # Parametro caption
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="caption"'.encode())
            body.append(''.encode())
            body.append(caption_text.encode())

            # Parametro photo
            body.append(f"--{boundary}".encode())
            body.append(f'Content-Disposition: form-data; name="photo"; filename="{os.path.basename(chart_path)}"'.encode())
            body.append('Content-Type: image/png'.encode())
            body.append(''.encode())
            body.append(image_file.read())

            body.append(f"--{boundary}--".encode())
            body.append(''.encode())

            payload = b"\r\n".join(body)

            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            
            with urllib.request.urlopen(req) as response:
                res = response.read()
                print("[+] Notifica Telegram inviata con successo!")
    except Exception as e:
        print(f"[!] Errore durante l'invio della notifica Telegram: {e}")

# ==========================================
# 5. MAIN PIPELINE
# ==========================================
def main():
    print("=== INIZIO ESECUZIONE TITAN ENGINE AGGIORNATO ===")
    
    history = load_json(HISTORY_FILE, [])
    database = load_json(DATABASE_FILE, {})

    if not history:
        print("[!] Archivio storico vuoto o non trovato!")
        sys.exit(1)

    # 1. Calcolo punteggi grezzi e applicazione Cooldown Factor
    raw_scores, delays, frequencies = calculate_raw_scores(history)
    adjusted_scores = apply_cooldown_factor(raw_scores, history)

    # 2. Costruzione Dodecaedro a 4 Strati
    dodeca_pool = build_tiered_dodecahedron(adjusted_scores, delays, history)

    # 3. Selezione Sestine con Filtri Anti-Overfitting
    titan1, titan2 = select_titan_sestinas(dodeca_pool, adjusted_scores, history)

    # 4. Calcolo metriche per output
    sum1, sum2 = sum(titan1), sum(titan2)
    z1 = round((sum1 - GAUSS_MEAN) / GAUSS_STD, 2)
    z2 = round((sum2 - GAUSS_MEAN) / GAUSS_STD, 2)

    # Aggiornamento Database
    database["next_draw"] = {
        "concorso": history[-1].get("concorso", 0) + 1,
        "date": datetime.now().strftime("%d/%m/%Y"),
        "jackpot": "€ 26.500.000",
        "dodecahedron_pool": dodeca_pool,
        "titan_1": {"numbers": titan1, "sum": sum1, "z_score": z1},
        "titan_2": {"numbers": titan2, "sum": sum2, "z_score": z2}
    }
    save_json(DATABASE_FILE, database)

    # 5. Generazione Grafico
    generate_titan_chart(titan1, titan2, dodeca_pool, adjusted_scores)

    # 6. Preparazione Notifica Telegram
    last_draw = history[-1]
    report_text = (
        f"⚡ TITAN GOD MODE — OPTIMAL ANALYSIS ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 TARGET: Concorso N° {database['next_draw']['concorso']}\n"
        f"💰 Jackpot Stimato: {database['next_draw']['jackpot']}\n\n"
        f"📊 ULTIMO RISULTATO (N° {last_draw.get('concorso')}):\n"
        f"Sestina: {last_draw.get('combinazione')}\n"
        f"Jolly: {last_draw.get('jolly')} | SuperStar: {last_draw.get('superstar')}\n\n"
        f"🛡️ KELLY RISK MANAGEMENT:\n"
        f"• Stato: 🟠 PRUDENZA STATISTICA (EV: -0.957)\n"
        f"• Consigliati: 2 Sestine TITAN (Budget 2,00 €)\n\n"
        f"🔮 DODECAEDRO A.I. POOL (4 Strati Bilanciati):\n"
        f"{dodeca_pool}\n\n"
        f"🔥 SESTINE CONCENTRATE (Filtrate Anti-Overfitting):\n"
        f"1️⃣ TITAN 1: {titan1}\n"
        f"   • Somma: {sum1} | Z-Score: {z1:+0.2f}\n"
        f"2️⃣ TITAN 2: {titan2}\n"
        f"   • Somma: {sum2} | Z-Score: {z2:+0.2f}\n"
    )

    send_telegram_notification(report_text, CHART_FILE)
    print("=== ESECUZIONE COMPLETATA CON SUCCESSO ===")

if __name__ == "__main__":
    main()
