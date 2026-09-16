"""
personal_stats.py
Analizza le sestine giocate DAVVERO dall'utente (da venus_played.json)
confrontandole con le estrazioni reali.

Calcola:
- Vincite reali (3+ punti)
- Totale speso/incassato
- ROI
- Statistiche per periodo
"""
import json
import os
from datetime import datetime


PLAYED_FILE = "venus_played.json"
HISTORY_FILE = "venus_history.json"

# Valori approssimativi premi SuperEnalotto (in €)
# Basati su medie storiche. Possono variare.
PRIZE_TABLE = {
    3: 25,       # media ~25€
    4: 300,      # media ~300€
    5: 25000,    # media ~25.000€
    "5+1": 500000,
    6: "JACKPOT",
}


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura {filepath}: {e}")
    return default


def calculate_hits(sestina, draw_numbers):
    """Calcola quanti numeri della sestina sono presenti nell'estrazione."""
    return len(set(sestina) & set(draw_numbers))


def get_prize_for_hits(hits):
    """Ritorna il premio stimato per un certo numero di punti."""
    if hits in PRIZE_TABLE:
        return PRIZE_TABLE[hits]
    return 0


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

    # Crea indice storico per concorso
    history_by_concorso = {}
    for d in history:
        c = d.get("concorso")
        if isinstance(c, int):
            history_by_concorso[c] = d

    # Statistiche
    total_spent = 0.0
    total_won = 0.0
    results = []
    hits_distribution = {i: 0 for i in range(7)}

    for play in played_list:
        concorso = play.get("concorso")
        sestine = play.get("sestine", [])
        cost = play.get("costo_eur", len(sestine) * 1.0)

        total_spent += cost

        # Cerca estrazione reale
        draw = history_by_concorso.get(concorso)
        if not draw:
            results.append({
                "concorso": concorso,
                "status": "pending",
                "message": "Estrazione non ancora disponibile",
            })
            continue

        real_numbers = draw.get("combinazione", [])
        if len(real_numbers) != 6:
            results.append({
                "concorso": concorso,
                "status": "invalid",
                "message": "Estrazione non valida",
            })
            continue

        # Calcola hit per ogni sestina
        hits_list = [calculate_hits(s, real_numbers) for s in sestine]
        best_hits = max(hits_list) if hits_list else 0

        # Premio stimato
        prize = get_prize_for_hits(best_hits)
        prize_value = prize if isinstance(prize, (int, float)) else 0
        total_won += prize_value

        hits_distribution[best_hits] += 1

        results.append({
            "concorso": concorso,
            "data": draw.get("data", "N/A"),
            "status": "completed",
            "sestine": sestine,
            "real_numbers": real_numbers,
            "hits_list": hits_list,
            "best_hits": best_hits,
            "prize_estimated": prize,
            "cost": cost,
        })

    # Statistiche finali
    completed = [r for r in results if r.get("status") == "completed"]
    pending = [r for r in results if r.get("status") == "pending"]

    n_completed = len(completed)
    hits_3plus = sum(1 for r in completed if r["best_hits"] >= 3)

    roi = 0.0
    if total_spent > 0:
        roi = round((total_won - total_spent) / total_spent * 100, 2)

    return {
        "total_plays": len(played_list),
        "completed": n_completed,
        "pending": len(pending),
        "total_spent": round(total_spent, 2),
        "total_won": round(total_won, 2),
        "roi_pct": roi,
        "balance": round(total_won - total_spent, 2),
        "hits_distribution": hits_distribution,
        "hits_3plus": hits_3plus,
        "hit_rate_3plus": round(hits_3plus / n_completed * 100, 2) if n_completed > 0 else 0.0,
        "results": results,
    }


def format_personal_report(stats):
    """Formatta il report personal stats per Telegram."""
    if not stats:
        return "📊 <b>STATISTICHE PERSONALI</b>\n\nNessuna giocata registrata.\nCompila <code>venus_played.json</code> per iniziare a tracciare le tue giocate."

    lines = []
    lines.append("💼 <b>STATISTICHE PERSONALI</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🎯 Giocate totali: <b>{stats['total_plays']}</b>")
    lines.append(f"✅ Completate: <b>{stats['completed']}</b> · ⏳ In attesa: <b>{stats['pending']}</b>")
    lines.append("")
    lines.append(f"💸 Speso: <b>€ {stats['total_spent']:.2f}</b>")
    lines.append(f"💰 Vinto: <b>€ {stats['total_won']:.2f}</b>")

    bal = stats["balance"]
    if bal >= 0:
        lines.append(f"✅ Bilancio: <b>+€ {bal:.2f}</b>")
    else:
        lines.append(f"⚠️ Bilancio: <b>€ {bal:.2f}</b>")

    lines.append(f"📈 ROI: <b>{stats['roi_pct']:+.2f}%</b>")
    lines.append("")
    lines.append("🎯 <b>Distribuzione punti:</b>")
    dist = stats["hits_distribution"]
    lines.append(f"  • 0 punti: {dist.get(0, 0)}")
    lines.append(f"  • 1 punto: {dist.get(1, 0)}")
    lines.append(f"  • 2 punti: {dist.get(2, 0)}")
    lines.append(f"  • <b>3 punti: {dist.get(3, 0)}</b>")
    lines.append(f"  • <b>4 punti: {dist.get(4, 0)}</b>")
    lines.append(f"  • <b>5 punti: {dist.get(5, 0)}</b>")
    lines.append(f"  • <b>6 punti: {dist.get(6, 0)}</b>")

    if stats["hits_3plus"] > 0:
        lines.append("")
        lines.append(f"✨ Hai fatto 3+ punti <b>{stats['hits_3plus']} volte</b> "
                     f"({stats['hit_rate_3plus']}%)")

    return "\n".join(lines)


if __name__ == "__main__":
    stats = analyze_played()
    if stats:
        print(format_personal_report(stats).replace("<b>", "").replace("</b>", "").replace("<code>", "").replace("</code>", ""))
    else:
        print("Nessuna giocata registrata.")
