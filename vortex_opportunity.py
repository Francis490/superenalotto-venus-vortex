"""
vortex_opportunity.py
VENUS VORTEX — Opportunity Engine v4.0 (SIMPLIFIED)

Cambio di paradigma (2026-10-01):
- RIMOSSI tutti i filtri complessi (anti-crowd, scoring, tiered pool).
- Generatore semplice: sestina con somma 240-310, seed per determinismo.
- Mantiene: EV calculator, rollover detector, budget mode, signature, backtest.
- Coerente con l'approccio di Aurora Engine v5.5.
"""
import hashlib
import random


SUM_MIN = 240
SUM_MAX = 310


# ==========================================
# 1. EV CALCULATOR
# ==========================================
def estimate_players(jackpot):
    if jackpot < 30_000_000:
        return 25_000_000
    elif jackpot < 50_000_000:
        return 50_000_000
    elif jackpot < 80_000_000:
        return 100_000_000
    elif jackpot < 120_000_000:
        return 180_000_000
    else:
        return 300_000_000


def calculate_ev(jackpot, anti_crowd_factor=2.5, ticket_cost=1.0):
    prob_6 = 1 / 622_614_630
    players = estimate_players(jackpot)
    expected_winners = max(1.0, players * prob_6)
    effective_jackpot = (jackpot / expected_winners) * anti_crowd_factor
    ev_6 = prob_6 * effective_jackpot
    ev_other = 0.35
    total_ev = ev_6 + ev_other - ticket_cost

    return {
        "jackpot": jackpot,
        "players_estimated": players,
        "expected_winners": round(expected_winners, 2),
        "effective_jackpot": round(effective_jackpot, 0),
        "ev_6_solo": round(ev_6, 4),
        "ev_total": round(total_ev, 4),
        "profitable": total_ev > 0,
        "recommendation": (
            "GIOCA FORTE" if total_ev > 0.5 else
            "GIOCA" if total_ev > 0 else
            "GIOCA MINIMO" if total_ev > -0.2 else
            "SALTA" if total_ev < -0.3 else
            "GIOCA POCO"
        ),
    }


# ==========================================
# 2. ROLLOVER DETECTOR
# ==========================================
def rollover_status(jackpot):
    if jackpot < 30_000_000:
        return {"level": "NORMALE", "emoji": "⚪",
                "message": "EV negativo. Gioca il minimo o salta."}
    elif jackpot < 50_000_000:
        return {"level": "INTERESSANTE", "emoji": "🟡",
                "message": "EV quasi neutro. Puoi giocare 2 sestine."}
    elif jackpot < 70_000_000:
        return {"level": "BUONA", "emoji": "🟠",
                "message": "EV vicino allo zero. Vale la pena giocare."}
    elif jackpot < 100_000_000:
        return {"level": "OTTIMA", "emoji": "🔴",
                "message": "EV positivo. Attack mode!"}
    else:
        return {"level": "ECCEZIONALE", "emoji": "🔥",
                "message": "EV molto positivo. Gioca forte!"}


# ==========================================
# 3. BUDGET MODE
# ==========================================
def determine_budget_mode(jackpot):
    ev_data = calculate_ev(jackpot)
    ev = ev_data["ev_total"]

    if ev < -0.55:
        return {"mode": "SKIP", "emoji": "🚫", "n_sestinas": 0,
                "cost_eur": 0.0, "ev": ev,
                "message": "EV molto negativo. Salta e risparmia."}
    elif ev < -0.35:
        return {"mode": "MINIMO", "emoji": "🟢", "n_sestinas": 1,
                "cost_eur": 1.0, "ev": ev,
                "message": "EV basso. 1 sestina (1,00 €)."}
    elif ev < -0.10:
        return {"mode": "NORMALE", "emoji": "🟡", "n_sestinas": 2,
                "cost_eur": 2.0, "ev": ev,
                "message": "EV neutro. 2 sestine (2,00 €)."}
    elif ev < 0.05:
        return {"mode": "ATTACK", "emoji": "🟠", "n_sestinas": 4,
                "cost_eur": 4.0, "ev": ev,
                "message": "EV positivo. Attack: 4 sestine (4,00 €)."}
    else:
        return {"mode": "ALL-IN", "emoji": "🔥", "n_sestinas": 6,
                "cost_eur": 6.0, "ev": ev,
                "message": "EV molto positivo! 6 sestine (6,00 €)."}


# ==========================================
# 4. VORTEX SIGNATURE
# ==========================================
def vortex_signature(sestina, concorso, data_str):
    payload = f"{concorso}|{data_str}|{'-'.join(map(str, sorted(sestina)))}"
    hash_full = hashlib.sha256(payload.encode()).hexdigest()
    year = data_str[-4:] if len(data_str) >= 4 else "0000"
    return f"VX-{year}-{concorso:03d}-{hash_full[:6].upper()}"


# ==========================================
# 5. BACKTEST
# ==========================================
def backtest(history, sestina1, sestina2=None, last_n=30):
    if not history or len(history) < 2:
        return None
    if len(history) < last_n + 1:
        last_n = len(history) - 1
    if last_n < 5:
        return None

    results = {"3_hits": 0, "4_hits": 0, "5_hits": 0, "total": 0}
    s1 = set(sestina1)
    s2 = set(sestina2) if sestina2 else s1

    for i in range(len(history) - last_n, len(history)):
        if i < 0:
            continue
        actual = set(history[i].get("combinazione", []))
        if not actual:
            continue
        hits1 = len(s1 & actual)
        hits2 = len(s2 & actual)
        best = max(hits1, hits2)
        if best == 3:
            results["3_hits"] += 1
        elif best == 4:
            results["4_hits"] += 1
        elif best >= 5:
            results["5_hits"] += 1
        results["total"] += 1

    if results["total"] > 0:
        results["hit_rate_3plus"] = round(
            (results["3_hits"] + results["4_hits"] + results["5_hits"])
            / results["total"] * 100, 2
        )
        results["baseline_expected"] = round(
            (1 / 327 + 1 / 11907 + 1 / 1250230 + 1 / 103769105 + 1 / 622614630)
            * 100, 2
        )
    return results


# ==========================================
# 6. BALANCE POOL (no-op per compatibilità)
# ==========================================
def balance_pool(dodeca_pool):
    """Mantenuta per compatibilità. Ritorna il pool così com'è."""
    return list(dodeca_pool)


# ==========================================
# 7. GENERATORE SEMPLICE
# ==========================================
def _generate_simple_sestina(pool, seed, verbose=False):
    """Una sestina con somma 240-310. Nessun filtro."""
    if len(pool) < 6:
        return None

    rng = random.Random(seed)
    candidates = []
    attempts = 0
    max_attempts = 500_000

    while len(candidates) < 10_000 and attempts < max_attempts:
        attempts += 1
        try:
            combo = tuple(sorted(rng.sample(pool, 6)))
        except ValueError:
            break
        if SUM_MIN <= sum(combo) <= SUM_MAX:
            candidates.append(combo)

    if not candidates:
        return None

    chosen = rng.choice(candidates)
    if verbose:
        print(f"[*] Sestina (seed={seed}): {list(chosen)} somma {sum(chosen)}")
    return chosen


# ==========================================
# 8. SELEZIONE MULTI-SESTINA
# ==========================================
def select_vortex_sestinas_multi(dodeca_pool, adjusted_scores, history,
                                  n_sestinas=2, seed=None):
    """Genera N sestine indipendenti con seed = seed + i."""
    if n_sestinas <= 0:
        return []

    if seed is None:
        seed = 1000

    results = []
    for i in range(n_sestinas):
        combo = _generate_simple_sestina(dodeca_pool, seed + i, verbose=True)
        if combo:
            results.append((tuple(combo), 1.0, 1.0, 1.0))
    return results


def select_vortex_sestinas(dodeca_pool, adjusted_scores, history,
                            top_n=1, seed=None):
    return select_vortex_sestinas_multi(
        dodeca_pool, adjusted_scores, history, n_sestinas=top_n, seed=seed
    )
