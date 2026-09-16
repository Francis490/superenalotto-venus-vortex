"""
backtest_e2e.py
Test end-to-end del bot: simula la generazione di sestine
su concorsi storici e verifica quanti punti avrebbe fatto.

Metodologia:
- Per ogni concorso di test, usa SOLO i dati precedenti
- Genera 2 sestine con il VORTEX ENGINE
- Confronta con l'estrazione reale
- Aggrega statistiche

NON è una predizione. È una valutazione delle performance storiche.
"""
import json
import os
from datetime import datetime

HISTORY_FILE = "venus_history.json"


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Errore lettura storico: {e}")
    return []


def generate_sestinas_from_history(history_subset, n_sestinas=2):
    """
    Genera sestine usando SOLO lo storico passato.
    Usa la stessa logica del bot (vortex_opportunity).
    """
    try:
        from vortex_opportunity import (
            select_vortex_sestinas_multi,
            balance_pool,
        )

        # Calcola score come fa il bot
        import math
        delays = {i: 0 for i in range(1, 91)}
        frequencies = {i: 0 for i in range(1, 91)}
        total_draws = len(history_subset)

        for num in range(1, 91):
            found = False
            for idx, draw in enumerate(reversed(history_subset)):
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

        # Cooldown
        adjusted_scores = raw_scores.copy()
        if len(history_subset) >= 3:
            t1_set = set(history_subset[-1].get("combinazione", []))
            t2_set = set(history_subset[-2].get("combinazione", []))
            t3_set = set(history_subset[-3].get("combinazione", []))
            for num in range(1, 91):
                if num in t1_set:
                    adjusted_scores[num] *= 0.25
                elif num in t2_set:
                    adjusted_scores[num] *= 0.60
                elif num in t3_set:
                    adjusted_scores[num] *= 0.85

        # Costruisci pool
        from scraper import build_tiered_dodecahedron
        dodeca_pool = build_tiered_dodecahedron(adjusted_scores, delays, history_subset)
        dodeca_pool = balance_pool(dodeca_pool)

        # Genera sestine
        vortex_sel = select_vortex_sestinas_multi(
            dodeca_pool, adjusted_scores, history_subset, n_sestinas=n_sestinas
        )
        return [list(s[0]) for s in vortex_sel]

    except Exception as e:
        print(f"[!] Errore generazione sestine: {e}")
        return []


def run_backtest(n_tests=10, n_sestinas=2):
    """
    Esegue il backtest sugli ultimi N concorsi.
    """
    history = load_history()
    if len(history) < n_tests + 30:
        print(f"[!] Storico insufficiente: {len(history)} estrazioni "
              f"(servono almeno {n_tests + 30})")
        return None

    # Ordina per concorso
    history = sorted(history, key=lambda x: x.get("concorso", 0))

    # Ultimi N concorsi come test
    test_range = range(len(history) - n_tests, len(history))

    print(f"=== BACKTEST END-TO-END ===")
    print(f"[*] Testando {n_tests} concorsi (ultimi {n_tests})")
    print(f"[*] Sestine per concorso: {n_sestinas}")
    print()

    results = []
    hits_distribution = {i: 0 for i in range(7)}

    for i in test_range:
        train_data = history[:i]  # Solo dati precedenti
        test_draw = history[i]

        concorso = test_draw.get("concorso")
        real_numbers = test_draw.get("combinazione", [])

        if len(real_numbers) != 6:
            continue

        # Genera sestine
        sestinas = generate_sestinas_from_history(train_data, n_sestinas)

        if not sestinas:
            print(f"[!] Concorso {concorso}: generazione fallita")
            continue

        # Calcola hit
        real_set = set(real_numbers)
        hits_list = [len(set(s) & real_set) for s in sestinas]
        best_hits = max(hits_list)

        hits_distribution[best_hits] += 1

        results.append({
            "concorso": concorso,
            "data": test_draw.get("data", "N/A"),
            "real_numbers": real_numbers,
            "sestinas": sestinas,
            "hits_list": hits_list,
            "best_hits": best_hits,
        })

        # Stampa progressiva
        marker = "🔥" if best_hits >= 3 else "  "
        print(f"{marker} Concorso {concorso}: "
              f"sestine={sestinas} → hits={hits_list} → best={best_hits}")

    # Statistiche finali
    n_tested = len(results)
    if n_tested == 0:
        return None

    hits_3plus = sum(1 for r in results if r["best_hits"] >= 3)

    stats = {
        "n_tested": n_tested,
        "hits_distribution": hits_distribution,
        "hits_3plus": hits_3plus,
        "hit_rate_3plus": round(hits_3plus / n_tested * 100, 2),
        "baseline_theoretical": 0.31,  # %
        "results": results,
    }

    # Baseline: probabilità teorica di 3+ in 2 sestine
    # P(3+) ≈ 0.31% per sestina → ~0.62% per 2 sestine
    stats["baseline_2sestinas"] = round(0.31 * 2, 2)

    return stats


def format_backtest_report(stats):
    """Formatta il report del backtest per Telegram."""
    if not stats:
        return "❌ Backtest non eseguito"

    lines = []
    lines.append("🔬 <b>BACKTEST END-TO-END</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append(f"📊 Concorsi testati: <b>{stats['n_tested']}</b>")
    lines.append(f"🎯 Sestine per concorso: 2")
    lines.append("")
    lines.append("📈 <b>Distribuzione punti:</b>")
    dist = stats["hits_distribution"]
    lines.append(f"  • 0 punti: {dist.get(0, 0)}")
    lines.append(f"  • 1 punto: {dist.get(1, 0)}")
    lines.append(f"  • 2 punti: {dist.get(2, 0)}")
    lines.append(f"  • <b>3 punti: {dist.get(3, 0)}</b>")
    lines.append(f"  • <b>4 punti: {dist.get(4, 0)}</b>")
    lines.append(f"  • <b>5 punti: {dist.get(5, 0)}</b>")
    lines.append(f"  • <b>6 punti: {dist.get(6, 0)}</b>")
    lines.append("")
    lines.append(f"✨ Hit rate 3+: <b>{stats['hit_rate_3plus']}%</b>")
    lines.append(f"📊 Baseline attesa: <b>{stats['baseline_2sestinas']}%</b>")

    if stats["hit_rate_3plus"] > stats["baseline_2sestinas"]:
        lines.append("")
        lines.append("✅ <b>Performance superiore alla baseline</b>")
    else:
        lines.append("")
        lines.append("⚠️ Performance nella media statistica")

    lines.append("")
    lines.append("<i>Nota: la baseline è la probabilità teorica "
                 "con 2 sestine casuali. Il bot non predice il futuro — "
                 "questa è una valutazione storica.</i>")

    return "\n".join(lines)


if __name__ == "__main__":
    stats = run_backtest(n_tests=10, n_sestinas=2)

    if stats:
        print()
        print("=" * 60)
        print("RIEPILOGO BACKTEST")
        print("=" * 60)
        print(f"Concorsi testati:    {stats['n_tested']}")
        print(f"Hit rate 3+:         {stats['hit_rate_3plus']}%")
        print(f"Baseline teorica:    {stats['baseline_2sestinas']}%")
        print()
        print("Distribuzione punti:")
        for k, v in sorted(stats["hits_distribution"].items()):
            print(f"  {k} punti: {v}")
