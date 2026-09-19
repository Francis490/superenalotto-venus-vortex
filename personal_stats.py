"""
personal_stats.py
Analizza le sestine giocate DAVVERO dall'utente (da venus_played.json)
confrontandole con le estrazioni reali.

Calcola:
- Vincite reali (2+ punti, perché il SuperEnalotto paga dal 2 in su)
- Totale speso/incassato
- ROI (complessivo e solo-completed)
- Statistiche per periodo

FIX (2026-09-19):
- #5: gestione esplicita del 6 punti (jackpot)
- #6: chiave storica composta (anno, concorso) per evitare collisioni 2025/2026
- #7: ROI calcolato anche solo sui "completed" (esclude le pending)
- #8: documentato che PRIZE_TABLE contiene stime, supporto per `premio_reale`
- Import load_json/save_json da venus_utils
"""
import json
import os
from venus_utils import (
    load_json,
    parse_date,
    get_concorso_key,
)

PLAYED_FILE = "venus_played.json"
HISTORY_FILE = "venus_history.json"
JACKPOT_FILE = "venus_jackpot.json"
MANUAL_OVERRIDE_FILE = "venus_manual_override.json"


# ==========================================
# TABELLA PREMI (STIME)
# ==========================================
# ATTENZIONE: il SuperEnalotto NON ha importi fissi per le categorie 3/4/5.
# Gli importi dipendono dal montepremi del concorso e dal numero di vincitori.
# Questi valori sono MEDIE TIPICHE usate come stima.
# Per dati reali, salvare `premio_reale` in ciascuna entry di venus_played.json.
PRIZE_TABLE = {
    2: 5,          # 5ª categoria — quota fissa
    3: 25,         # 4ª categoria — media tipica (VARIA)
    4: 300,        # 3ª categoria — media tipica (VARIA)
    5: 25000,      # 2ª categoria — media tipica (VARIA)
    "5+1": 500000, # 1ª categoria — media tipica (VARIA)
    # 6 punti → jackpot (valore variabile, letto da venus_jackpot.json)
}


# ==========================================
# UTILITY
# ==========================================
def calculate_hits(sestina, draw_numbers):
    """Calcola quanti numeri della sestina sono presenti nell'estrazione."""
    return len(set(sestina) & set(draw_numbers))


def get_current_jackpot():
    """
    Legge il jackpot corrente da override manuale o fallback su venus_jackpot.json.
    Usato per stimare la vincita in caso di 6 punti.
    """
    if os.path.exists(MANUAL_OVERRIDE_FILE):
        data = load_json(MANUAL_OVERRIDE_FILE, {})
        if isinstance(data.get("jackpot"), int) and data["jackpot"] > 0:
            return data["jackpot"]
    if os.path.exists(JACKPOT_FILE):
        data = load_json(JACKPOT_FILE, {})
        if isinstance(data.get("jackpot"), int) and data["jackpot"] > 0:
            return data["jackpot"]
    return None


def get_prize_for_hits(hits, jackpot_value=None, premium_real=None):
    """
    Ritorna il premio stimato per un certo numero di punti.

    - Se `premium_real` è fornito, lo usa (dato reale).
    - Se hits==6, ritorna il jackpot_value (o "JACKPOT_UNKNOWN" se assente).
    - Altrimenti cerca nella PRIZE_TABLE.
    """
    if premium_real is not None:
        return premium_real

    if hits == 6:
        return jackpot_value if jackpot_value else "JACKPOT_UNKNOWN"

    return PRIZE_TABLE.get(hits, 0)


def build_history_index(history):
    """
    Crea un indice {(anno, concorso): entry} per gestire correttamente
    la collisione tra concorsi 2025 (offset +1000) e 2026 (1-150).

    FIX #6: prima l'indice usava solo `concorso` come chiave e
    sovrascriveva le entry 2025/2026 con stesso numero.
    """
    index = {}
    for d in history:
        c = d.get("concorso")
        if not isinstance(c, int):
            continue
        year = parse_date(d.get("data", ""))[0] or None
        key = (year, c)
        index[key] = d
    return index


# ==========================================
# ANALISI PRINCIPALE
# ==========================================
def analyze_played():
    """
    Analizza le sestine giocate confrontandole con le estrazioni reali.
    Ritorna statistiche aggregate.
    """
    played_data = load_json(PLAYED_FILE, {"played": []})
    history = load_json(HISTORY_FILE, [])

    played_list = played_data.get("played", [])
    if not played_list:
        return None

    # FIX #6: indice con chiave (anno, concorso)
    history_by_key = build_history_index(history)

    # Jackpot corrente per stimare eventuali 6 punti
    jackpot_value = get_current_jackpot()

    # Statistiche
    total_spent = 0.0
    total_won = 0.0
    spent_completed = 0.0
    won_completed = 0.0
    results = []
    hits_distribution = {i: 0 for i in range(7)}

    for play in played_list:
        concorso = play.get("concorso")
        data_play = play.get("data", "")
        sestine = play.get("sestine", [])
        cost = play.get("costo_eur", len(sestine) * 1.0)

        total_spent += cost

        # FIX #6: cerca con chiave (anno, concorso)
        year = parse_date(data_play)[0] or None
        draw = history_by_key.get((year, concorso))

        if not draw:
            results.append({
                "concorso": concorso,
                "data": data_play,
                "status": "pending",
                "message": "Estrazione non ancora disponibile",
                "cost": cost,
            })
            continue

        real_numbers = draw.get("combinazione", [])
        if len(real_numbers) != 6:
            results.append({
                "concorso": concorso,
                "data": data_play,
                "status": "invalid",
                "message": "Estrazione non valida",
                "cost": cost,
            })
            continue

        # Calcola hit per ogni sestina
        hits_list = [calculate_hits(s, real_numbers) for s in sestine]
        best_hits = max(hits_list) if hits_list else 0

        # FIX #5 + #8: premio con supporto per jackpot e premio_reale
        prize_total = 0
        jackpot_triggered = False
        premium_real = play.get("premio_reale")  # opzionale in venus_played.json

        for hits in hits_list:
            p = get_prize_for_hits(hits, jackpot_value, premium_real)
            if p == "JACKPOT_UNKNOWN":
                jackpot_triggered = True
                continue
            if isinstance(p, (int, float)):
                prize_total += p

        # Se c'è stato un 6 punti ma non conosciamo il jackpot, segnala
        if jackpot_triggered:
            results.append({
                "concorso": concorso,
                "data": draw.get("data", "N/A"),
                "status": "completed_jackpot_unknown",
                "sestine": sestine,
                "real_numbers": real_numbers,
                "hits_list": hits_list,
                "best_hits": best_hits,
                "prize_estimated": None,
                "cost": cost,
                "message": "6 punti! Jackpot non determinabile automaticamente.",
            })
            total_won += 0  # non possiamo stimare
            spent_completed += cost
            won_completed += 0
            hits_distribution[best_hits] += 1
            continue

        total_won += prize_total
        spent_completed += cost
        won_completed += prize_total
        hits_distribution[best_hits] += 1

        results.append({
            "concorso": concorso,
            "data": draw.get("data", "N/A"),
            "status": "completed",
            "sestine": sestine,
            "real_numbers": real_numbers,
            "hits_list": hits_list,
            "best_hits": best_hits,
            "prize_estimated": prize_total,
            "prize_real": premium_real,
            "cost": cost,
        })

    # Statistiche finali
    completed = [r for r in results
                 if r.get("status", "").startswith("completed")]
    pending = [r for r in results if r.get("status") == "pending"]

    n_completed = len(completed)
    hits_2plus = sum(1 for r in completed if r.get("best_hits", 0) >= 2)
    hits_3plus = sum(1 for r in completed if r.get("best_hits", 0) >= 3)

    # FIX #7: ROI complessivo e ROI solo-completed
    roi = 0.0
    if total_spent > 0:
        roi = round((total_won - total_spent) / total_spent * 100, 2)

    roi_completed = 0.0
    if spent_completed > 0:
        roi_completed = round(
            (won_completed - spent_completed) / spent_completed * 100, 2
        )

    return {
        "total_plays": len(played_list),
        "completed": n_completed,
        "pending": len(pending),
        "total_spent": round(total_spent, 2),
        "total_won": round(total_won, 2),
        "roi_pct": roi,
        # FIX #7: ROI solo sulle giocate completate
        "spent_completed": round(spent_completed, 2),
        "won_completed": round(won_completed, 2),
        "roi_completed_pct": roi_completed,
        "balance": round(total_won - total_spent, 2),
        "hits_distribution": hits_distribution,
        "hits_2plus": hits_2plus,
        "hits_3plus": hits_3plus,
        "hit_rate_2plus": round(hits_2plus / n_completed * 100, 2) if n_completed > 0 else 0.0,
        "hit_rate_3plus": round(hits_3plus / n_completed * 100, 2) if n_completed > 0 else 0.0,
        "jackpot_current": jackpot_value,
        "results": results,
    }


# ==========================================
# FORMATTAZIONE REPORT
# ==========================================
def format_personal_report(stats):
    """Formatta il report personal stats per Telegram."""
    if not stats:
        return ("📊 <b>STATISTICHE PERSONALI</b>\n\n"
                "Nessuna giocata registrata.\n"
                "Compila <code>venus_played.json</code> per iniziare a tracciare le tue giocate.")

    lines = []
    lines.append("💼 <b>STATISTICHE PERSONALI</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🎯 Giocate totali: <b>{stats['total_plays']}</b>")
    lines.append(f"✅ Completate: <b>{stats['completed']}</b> · "
                 f"⏳ In attesa: <b>{stats['pending']}</b>")
    lines.append("")
    lines.append(f"💸 Speso: <b>€ {stats['total_spent']:.2f}</b>")
    lines.append(f"💰 Vinto: <b>€ {stats['total_won']:.2f}</b>")

    bal = stats["balance"]
    if bal > 0:
        lines.append(f"✅ Bilancio: <b>+€ {bal:.2f}</b>")
    elif bal < 0:
        lines.append(f"⚠️ Bilancio: <b>€ {bal:.2f}</b>")
    else:
        lines.append(f"⚪ Bilancio: <b>€ {bal:.2f}</b>")

    lines.append(f"📈 ROI: <b>{stats['roi_pct']:+.2f}%</b>")

    # FIX #7: mostra ROI solo-completed se differisce da quello totale
    if stats.get("pending", 0) > 0 and stats.get("spent_completed", 0) > 0:
        roi_comp = stats.get("roi_completed_pct", 0)
        lines.append(f"    (solo completed: <b>{roi_comp:+.2f}%</b>)")

    lines.append("")
    lines.append("🎯 <b>Distribuzione punti:</b>")
    dist = stats["hits_distribution"]
    lines.append(f"  • 0 punti: {dist.get(0, 0)}")
    lines.append(f"  • 1 punto: {dist.get(1, 0)}")
    lines.append(f"  • <b>2 punti: {dist.get(2, 0)}</b>")
    lines.append(f"  • <b>3 punti: {dist.get(3, 0)}</b>")
    lines.append(f"  • <b>4 punti: {dist.get(4, 0)}</b>")
    lines.append(f"  • <b>5 punti: {dist.get(5, 0)}</b>")
    lines.append(f"  • <b>6 punti: {dist.get(6, 0)}</b>")

    if stats.get("hits_2plus", 0) > 0:
        lines.append("")
        lines.append(f"✨ Hai fatto 2+ punti <b>{stats['hits_2plus']} volte</b> "
                     f"({stats['hit_rate_2plus']}%)")

    if stats.get("hits_3plus", 0) > 0:
        lines.append(f"🔥 Hai fatto 3+ punti <b>{stats['hits_3plus']} volte</b> "
                     f"({stats['hit_rate_3plus']}%)")

    # Nota informativa sui premi
    lines.append("")
    lines.append("<i>ℹ️ Importi 3/4/5 punti sono stime medie. "
                 "Per dati reali, salva <code>premio_reale</code> in venus_played.json.</i>")

    return "\n".join(lines)


if __name__ == "__main__":
    stats = analyze_played()
    if stats:
        out = format_personal_report(stats)
        print(out.replace("<b>", "").replace("</b>", "")
                 .replace("<code>", "").replace("</code>", "")
                 .replace("<i>", "").replace("</i>", ""))
    else:
        print("Nessuna giocata registrata.")
