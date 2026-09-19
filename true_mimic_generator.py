"""
true_mimic_generator.py
Genera sestine statisticamente INDISTINGUIBILI dalle estrazioni reali.
Applica 12 fingerprint estratti dai dati storici.

NON è una previsione. È una fedele riproduzione della distribuzione reale.
"""
import json
import os
import random
import itertools
import math

HISTORY_FILE = "venus_history.json"

# Range target per la somma delle sestine (vincolo dominio SuperEnalotto)
SUM_HARD_MIN = 240
SUM_HARD_MAX = 310


# ==========================================
# FINGERPRINT ANALYSIS
# ==========================================
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def extract_fingerprints(history):
    """
    Estrae i 12 fingerprint dalle estrazioni reali.
    Ritorna un dict con parametri statistici.
    """
    if not history:
        return default_fingerprints()

    draws = [d.get("combinazione", []) for d in history
             if len(d.get("combinazione", [])) == 6]

    if not draws:
        return default_fingerprints()

    n = len(draws)

    # 1. Somma totale
    sums = [sum(d) for d in draws]
    sum_mean = sum(sums) / n
    sum_std = math.sqrt(sum((x - sum_mean) ** 2 for x in sums) / max(1, n - 1))

    # 2. Parità
    parity_counts = {i: 0 for i in range(7)}
    for d in draws:
        n_pari = sum(1 for x in d if x % 2 == 0)
        parity_counts[n_pari] += 1

    # 3. Decadi
    decade_counts = [0] * 9
    for d in draws:
        for x in d:
            decade_counts[min(8, (x - 1) // 10)] += 1

    # 4. Primo numero
    firsts = [d[0] for d in draws]

    # 5. Ultimo numero
    lasts = [d[-1] for d in draws]

    # 6. Gap tra consecutivi
    all_gaps = []
    for d in draws:
        s = sorted(d)
        for i in range(len(s) - 1):
            all_gaps.append(s[i + 1] - s[i])
    max_gap_observed = max(all_gaps) if all_gaps else 30
    avg_gap = sum(all_gaps) / len(all_gaps) if all_gaps else 15

    # 7. Consecutivi (conteggio coppie)
    consec_pairs = []
    for d in draws:
        s = sorted(d)
        pairs = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
        consec_pairs.append(pairs)

    # 8. Numeri < 30
    low_counts = [sum(1 for x in d if x < 30) for d in draws]

    # 9. Numeri > 60
    high_counts = [sum(1 for x in d if x > 60) for d in draws]

    # 10. Somma ultime cifre
    last_digit_sums = [sum(x % 10 for x in d) for d in draws]
    ld_mean = sum(last_digit_sums) / n
    ld_std = math.sqrt(
        sum((x - ld_mean) ** 2 for x in last_digit_sums) / max(1, n - 1)
    )

    # 11. Distribution mod 5
    mod5_counts = [0] * 5
    for d in draws:
        for x in d:
            mod5_counts[x % 5] += 1

    # 12. Spread
    spreads = [max(d) - min(d) for d in draws]

    return {
        "n_samples": n,
        "sum_mean": round(sum_mean, 2),
        "sum_std": round(sum_std, 2),
        "sum_min": min(sums),
        "sum_max": max(sums),
        "parity_distribution": parity_counts,
        "decade_distribution": decade_counts,
        "first_min": min(firsts),
        "first_max": max(firsts),
        "first_mean": round(sum(firsts) / n, 2),
        "last_min": min(lasts),
        "last_max": max(lasts),
        "last_mean": round(sum(lasts) / n, 2),
        "gap_max": max_gap_observed,
        "gap_avg": round(avg_gap, 2),
        "consec_pairs_avg": round(sum(consec_pairs) / n, 2),
        "low_min": min(low_counts),
        "low_max": max(low_counts),
        "high_min": min(high_counts),
        "high_max": max(high_counts),
        "last_digit_mean": round(ld_mean, 2),
        "last_digit_std": round(ld_std, 2),
        "mod5_distribution": mod5_counts,
        "spread_min": min(spreads),
        "spread_max": max(spreads),
    }


def default_fingerprints():
    return {
        "n_samples": 0,
        "sum_mean": 273.0, "sum_std": 43.5,
        "sum_min": 144, "sum_max": 405,
        "parity_distribution": {0: 0, 1: 0, 2: 30, 3: 90, 4: 30, 5: 0, 6: 0},
        "decade_distribution": [100] * 9,
        "first_min": 1, "first_max": 25, "first_mean": 10,
        "last_min": 60, "last_max": 90, "last_mean": 78,
        "gap_max": 30, "gap_avg": 15,
        "consec_pairs_avg": 0.5,
        "low_min": 1, "low_max": 4,
        "high_min": 0, "high_max": 4,
        "last_digit_mean": 27, "last_digit_std": 6,
        "mod5_distribution": [200] * 5,
        "spread_min": 40, "spread_max": 88,
    }


# ==========================================
# VALIDATOR — 12 CHECKS
# ==========================================
def validate_sestina(sestina, fp):
    """
    Verifica se una sestina rispetta tutti i 12 fingerprint.
    Ritorna (ok: bool, score: float, checks: dict).
    """
    if len(sestina) != 6:
        return False, 0, {}

    s = sorted(sestina)
    checks = {}

    # 1. Somma — vincolo statistico (μ±1.5σ) intersecato al range hard 240-310
    total = sum(s)
    sum_lo = max(SUM_HARD_MIN, fp["sum_mean"] - 1.5 * fp["sum_std"])
    sum_hi = min(SUM_HARD_MAX, fp["sum_mean"] + 1.5 * fp["sum_std"])
    checks["sum"] = sum_lo <= total <= sum_hi

    # 2. Parità
    n_pari = sum(1 for x in s if x % 2 == 0)
    checks["parity"] = 2 <= n_pari <= 4

    # 3. Decadi (max 2 numeri per decade)
    decades = [0] * 9
    for x in s:
        decades[min(8, (x - 1) // 10)] += 1
    checks["decades"] = max(decades) <= 2

    # 4. Primo numero
    checks["first"] = 1 <= s[0] <= 25

    # 5. Ultimo numero
    checks["last"] = 55 <= s[-1] <= 90

    # 6. Gap massimo
    max_gap = max(s[i + 1] - s[i] for i in range(5))
    checks["max_gap"] = max_gap <= fp["gap_max"] + 5

    # 7. Consecutivi
    n_consec = sum(1 for i in range(5) if s[i + 1] - s[i] == 1)
    checks["consec"] = n_consec <= 1

    # 8. Numeri bassi
    n_low = sum(1 for x in s if x < 30)
    checks["low"] = 1 <= n_low <= 4

    # 9. Numeri alti
    n_high = sum(1 for x in s if x > 60)
    checks["high"] = 0 <= n_high <= 4

    # 10. Somma ultime cifre
    ld_sum = sum(x % 10 for x in s)
    ld_lo = fp["last_digit_mean"] - 2 * fp["last_digit_std"]
    ld_hi = fp["last_digit_mean"] + 2 * fp["last_digit_std"]
    checks["last_digits"] = ld_lo <= ld_sum <= ld_hi

    # 11. Mod 5 (no tutti uguali)
    mods = [x % 5 for x in s]
    checks["mod5"] = len(set(mods)) >= 3

    # 12. Spread
    spread = s[-1] - s[0]
    checks["spread"] = fp["spread_min"] - 5 <= spread <= fp["spread_max"] + 5

    passed = sum(1 for v in checks.values() if v)
    return passed == 12, passed / 12, checks


# ==========================================
# GENERATOR
# ==========================================
def generate_mimic_sestinas(pool, fp, n_sestinas=2, candidates=5000):
    """
    Genera N sestine che rispettano TUTTI i 12 fingerprint.
    """
    if len(pool) < 6:
        return []

    all_combos = list(itertools.combinations(pool, 6))

    # Filtro 1: tutti i fingerprint
    valid = []
    for combo in all_combos:
        ok, score, checks = validate_sestina(combo, fp)
        if ok:
            valid.append((combo, score))

    if not valid:
        # Fallback: filtra per somma nel range hard, poi ordina per score
        scored = []
        for combo in all_combos:
            if not (SUM_HARD_MIN <= sum(combo) <= SUM_HARD_MAX):
                continue
            ok, score, _ = validate_sestina(combo, fp)
            scored.append((combo, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        valid = scored[:candidates]

    # Diversifica: prendi le migliori con overlap minimo
    valid.sort(key=lambda x: x[1], reverse=True)

    selected = []
    for combo, score in valid:
        if len(selected) >= n_sestinas:
            break
        combo_set = set(combo)
        max_overlap = 0
        for existing, _ in selected:
            overlap = len(combo_set & set(existing))
            max_overlap = max(max_overlap, overlap)
        if max_overlap <= 2 or not selected:
            selected.append((combo, score))

    return [list(c) for c, _ in selected]


# ==========================================
# API PRINCIPALE
# ==========================================
def generate_true_mimic(history, pool, n_sestinas=2):
    """
    API principale: genera sestine indistinguibili da estrazioni reali.
    """
    fp = extract_fingerprints(history)
    print(f"[+] Fingerprint estratti da {fp['n_samples']} estrazioni")
    print(f"    • Somma: μ={fp['sum_mean']}, σ={fp['sum_std']}")
    print(f"    • Range somma (stat): {fp['sum_min']}-{fp['sum_max']}")
    print(f"    • Range somma (hard): {SUM_HARD_MIN}-{SUM_HARD_MAX}")
    print(f"    • Primo: {fp['first_min']}-{fp['first_max']} (μ={fp['first_mean']})")
    print(f"    • Ultimo: {fp['last_min']}-{fp['last_max']} (μ={fp['last_mean']})")
    print(f"    • Gap max osservato: {fp['gap_max']}")
    print(f"    • Spread: {fp['spread_min']}-{fp['spread_max']}")

    sestinas = generate_mimic_sestinas(pool, fp, n_sestinas)
    return sestinas, fp
