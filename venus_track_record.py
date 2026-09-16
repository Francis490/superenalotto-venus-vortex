"""
venus_track_record.py
Gestisce il track record delle sestine generate.
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
