"""
venus_track_record.py
Gestisce il track record delle sestine generate.
Include rilevamento vincite (3+, 4+, 5+, 6 punti).
"""
import json
import os
from datetime import datetime

TRACK_FILE = "venus_track_record.json"


def load_track():
    if os.path.exists(TRACK_FILE):
        try:
            with open(TRACK_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"records": []}


def save_track(data):
    try:
        with open(TRACK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[+] Track record salvato: {TRACK_FILE}")
    except Exception as e:
        print(f"[!] Errore salvataggio track: {e}")


def record_predictions(target_concorso, sestinas, mode):
    """Salva le sestine generate per un concorso target."""
    if not sestinas:
        return

    track = load_track()
    records = track.get("records", [])

    for r in records:
        if r.get("target_concorso") == target_concorso:
            existing = r.get("sestinas", [])
            if existing != sestinas:
                r["sestinas"] = sestinas
                r["mode"] = mode
                r["generated_at"] = datetime.now().isoformat()
                save_track(track)
                print(f"[+] Track record aggiornato per concorso {target_concorso}")
            return

    records.append({
        "target_concorso": target_concorso,
        "generated_at": datetime.now().isoformat(),
        "mode": mode,
        "sestinas": sestinas,
        "result": None,
    })

    save_track(track)
    print(f"[+] Track record: registrato concorso {target_concorso} "
          f"({len(sestinas)} sestine)")


def update_with_result(concorso, real_numbers):
    """Calcola i punti per le sestine che puntavano a un concorso."""
    if not real_numbers or len(real_numbers) != 6:
        return None

    track = load_track()
    records = track.get("records", [])
    real_set = set(real_numbers)

    updated = None
    for r in records:
        if r.get("target_concorso") == concorso and r.get("result") is None:
            sestinas = r.get("sestinas", [])
            hits_list = [len(set(s) & real_set) for s in sestinas]
            best = max(hits_list) if hits_list else 0

            r["result"] = {
                "real_numbers": real_numbers,
                "hits_per_sestina": hits_list,
                "best_hits": best,
                "checked_at": datetime.now().isoformat(),
            }
            updated = r
            print(f"[+] Track: concorso {concorso} -> miglior esito = {best} punti")

    if updated:
        save_track(track)
    return updated


def detect_wins(concorso, real_numbers):
    """
    Rileva se ci sono state vincite significative (3+ punti).
    Ritorna un dict con info dettagliate sulle vincite, o None se nessuna.
    """
    if not real_numbers or len(real_numbers) != 6:
        return None

    track = load_track()
    records = track.get("records", [])
    real_set = set(real_numbers)

    for r in records:
        if r.get("target_concorso") == concorso:
            sestinas = r.get("sestinas", [])
            mode = r.get("mode", "NORMALE")
            generated_at = r.get("generated_at", "N/A")

            # Analizza ogni sestina
            wins = []
            for i, s in enumerate(sestinas):
                hits = len(set(s) & real_set)
                if hits >= 3:
                    wins.append({
                        "index": i + 1,
                        "sestina": list(s),
                        "hits": hits,
                    })

            if wins:
                return {
                    "concorso": concorso,
                    "real_numbers": real_numbers,
                    "mode": mode,
                    "generated_at": generated_at,
                    "wins": wins,
                    "total_sestinas": len(sestinas),
                    "best_hits": max(w["hits"] for w in wins),
                }

    return None


def format_win_notification(win_info):
    """
    Formatta una notifica di VINCITA in HTML per Telegram.
    """
    if not win_info:
        return None

    concorso = win_info["concorso"]
    real_numbers = win_info["real_numbers"]
    wins = win_info["wins"]
    best = win_info["best_hits"]
    mode = win_info["mode"]

    # Emoji e messaggio in base al livello di vincita
    if best == 6:
        header = "🏆🏆🏆 JACKPOT! 🏆🏆🏆"
        emoji = "💰💰💰"
        msg = "SEI UN MILIONARIO!"
    elif best == 5:
        header = "🔥🔥🔥 VINCITA ECCEZIONALE! 🔥🔥🔥"
        emoji = "🎉🎉🎉"
        msg = "5 PUNTI — vincita importante!"
    elif best == 4:
        header = "🎉🎉 VINCITA! 🎉🎉"
        emoji = "💸💸"
        msg = "4 PUNTI — complimenti!"
    else:  # 3
        header = "🎯 VINCITA! 🎯"
        emoji = "✨"
        msg = "3 PUNTI — vincita!"

    lines = []
    lines.append(f"<b>{header}</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"🎯 <b>Concorso N° {concorso}</b>")
    lines.append(f"📊 Estrazione: <code>{' · '.join(str(n).zfill(2) for n in real_numbers)}</code>")
    lines.append(f"🎛️ Modalità: {mode}")
    lines.append("")
    lines.append(f"<b>{emoji} {msg}</b>")
    lines.append("")

    for w in wins:
        sestina_str = " · ".join(str(n).zfill(2) for n in w["sestina"])
        lines.append(f"✨ Sestina #{w['index']}: <code>[{sestina_str}]</code>")
        lines.append(f"   ➜ <b>{w['hits']} punti</b>")

    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("🌪️ <b>Venus Vortex — Cosmic Pattern Engine</b>")

    return "\n".join(lines)


def get_stats():
    """Ritorna statistiche aggregate del track record."""
    track = load_track()
    records = track.get("records", [])

    completed = [r for r in records if r.get("result") is not None]
    total = len(completed)

    if total == 0:
        return {
            "total": 0,
            "pending": len(records),
            "distribution": {str(i): 0 for i in range(6)},
            "hits_3plus": 0,
            "hit_rate_3plus": 0.0,
        }

    dist = {str(i): 0 for i in range(6)}
    for r in completed:
        best = r["result"].get("best_hits", 0)
        dist[str(best)] = dist.get(str(best), 0) + 1

    hits_3plus = dist["3"] + dist["4"] + dist["5"]

    return {
        "total": total,
        "pending": len(records) - total,
        "distribution": dist,
        "hits_3plus": hits_3plus,
        "hit_rate_3plus": round(hits_3plus / total * 100, 2) if total > 0 else 0.0,
    }


def format_stats_for_report(stats):
    """Formatta il track record per il report Telegram."""
    if not stats or stats.get("total", 0) == 0:
        pending = stats.get("pending", 0) if stats else 0
        return f"Nessun dato ancora ({pending} in attesa)"

    total = stats["total"]
    dist = stats["distribution"]

    lines = [
        f"📊 Concorsi tracciati: {total} (+{stats['pending']} in attesa)",
        f"🎯 3 punti: {dist.get('3', 0)} · 4 punti: {dist.get('4', 0)} · 5 punti: {dist.get('5', 0)}",
        f"📈 Hit rate 3+: {stats['hit_rate_3plus']}%",
    ]
    return "\n".join(lines)
