"""
vortex_opportunity.py
VENUS VORTEX — Opportunity Engine v3.3

Novità v3.3:
- determine_budget_mode: modula n° sestine in base all'EV (soglie realistiche)
- select_vortex_sestinas_multi: genera N sestine complementari
- Balance pool 4/4/4
- Somma 240-310 obbligatoria
- SKIP mode = 0 sestine
"""
import hashlib
import itertools


# ==========================================
# 1. ANTI-CROWD FILTER
# ==========================================
def anti_crowd_weight(number):
    if 1 <= number <= 31:
        return 0.4
    elif 32 <= number <= 45:
        return 0.7
    elif 46 <= number <= 60:
        return 1.2
    elif 61 <= number <= 90:
        return 1.5
    return 1.0


def has_visual_pattern(sestina):
    s = sorted(sestina)
    consecutivi = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
    if consecutivi >= 2:
        return True
    decadi = set((n - 1) // 10 for n in s)
    if len(decadi) <= 2:
        return True
    if all(n % 5 == 0 for n in s):
        return True
    if all(n % 10 == 0 for n in s):
        return True
    return False


def anti_crowd_score(sestina):
    weight_sum = sum(anti_crowd_weight(n) for n in sestina)
    pattern_penalty = 0.5 if has_visual_pattern(sestina) else 1.0
    return weight_sum * pattern_penalty


# ==========================================
# 2. EV CALCULATOR
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
# 3. ROLLOVER DETECTOR
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
# 3-bis. BUDGET MODE DINAMICO (v3.3)
# ==========================================
def determine_budget_mode(jackpot):
    """
    Modula il numero di sestine in base all'EV.
    Soglie realistiche per SuperEnalotto (EV tipico -0.35/-0.55).
    """
    ev_data = calculate_ev(jackpot)
    ev = ev_data["ev_total"]

    if ev < -0.55:
        return {
            "mode": "SKIP",
            "emoji": "🚫",
            "n_sestinas": 0,
            "cost_eur": 0.0,
            "ev": ev,
            "message": "EV molto negativo. Salta e risparmia.",
        }
    elif ev < -0.35:
        return {
            "mode": "MINIMO",
            "emoji": "🟢",
            "n_sestinas": 1,
            "cost_eur": 0.5,
            "ev": ev,
            "message": "EV basso. 1 sestina.",
        }
    elif ev < -0.10:
        return {
            "mode": "NORMALE",
            "emoji": "🟡",
            "n_sestinas": 2,
            "cost_eur": 1.0,
            "ev": ev,
            "message": "EV neutro. 2 sestine.",
        }
    elif ev < 0.05:
        return {
            "mode": "ATTACK",
            "emoji": "🟠",
            "n_sestinas": 4,
            "cost_eur": 2.0,
            "ev": ev,
            "message": "EV positivo. Attack: 4 sestine.",
        }
    else:
        return {
            "mode": "ALL-IN",
            "emoji": "🔥",
            "n_sestinas": 6,
            "cost_eur": 3.0,
            "ev": ev,
            "message": "EV molto positivo! 6 sestine.",
        }


# ==========================================
# 4. VORTEX SIGNATURE
# ==========================================
def vortex_signature(sestina, concorso, data_str):
    payload = f"{concorso}|{data_str}|{'-'.join(map(str, sorted(sestina)))}"
    hash_full = hashlib.sha256(payload.encode()).hexdigest()
    year = data_str[-4:] if len(data_str) >= 4 else "0000"
    return f"VX-{year}-{concorso:03d}-{hash_full[:6].upper()}"


# ==========================================
# 5. BACKTEST ENGINE
# ==========================================
def backtest(history, sestina1, sestina2, last_n=30):
    if not history or len(history) < 2:
        return None
    if len(history) < last_n + 1:
        last_n = len(history) - 1
    if last_n < 5:
        return None

    results = {"3_hits": 0, "4_hits": 0, "5_hits": 0, "total": 0}
    s1, s2 = set(sestina1), set(sestina2)

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
# 6. BALANCE POOL
# ==========================================
def balance_pool(dodeca_pool):
    bassi = sorted([n for n in dodeca_pool if 1 <= n <= 30])
    medi = sorted([n for n in dodeca_pool if 31 <= n <= 60])
    alti = sorted([n for n in dodeca_pool if 61 <= n <= 90])

    target = 4
    balanced = []
    balanced.extend(bassi[:target])
    balanced.extend(medi[:target])
    balanced.extend(alti[:target])

    if len(balanced) < 12:
        restanti = [n for n in dodeca_pool if n not in balanced]
        restanti.sort()
        balanced.extend(restanti[:12 - len(balanced)])

    return sorted(balanced[:12])


# ==========================================
# 7. SCORING
# ==========================================
def _score_realistic(combo, adjusted_scores):
    s = sorted(combo)
    total = sum(s)
    dist_from_mean = abs(total - 273)
    pari = sum(1 for n in s if n % 2 == 0)
    parity_penalty = abs(pari - 3) * 5
    bassi = sum(1 for n in s if n <= 45)
    balance_penalty = abs(bassi - 3) * 5
    decadi = len(set((n - 1) // 10 for n in s))
    decades_bonus = decadi * 3
    stat_score = sum(adjusted_scores[n] for n in combo)
    crowd = anti_crowd_score(combo)

    return (stat_score * crowd
            - dist_from_mean * 0.5
            - parity_penalty
            - balance_penalty
            + decades_bonus)


def _score_assassin(combo, adjusted_scores):
    s = sorted(combo)
    high_count = sum(1 for n in s if n > 55)
    crowd = anti_crowd_score(combo) ** 1.3
    stat_score = sum(adjusted_scores[n] for n in combo)
    high_bonus = high_count * 12
    return stat_score * crowd + high_bonus


# ==========================================
# 8. SELEZIONE MULTI-SESTINA (v3.3)
# ==========================================
def _build_candidates(dodeca_pool, adjusted_scores, history):
    all_combos = list(itertools.combinations(dodeca_pool, 6))
    t1_set = set(history[-1].get("combinazione", [])) if history else set()

    base = []
    for combo in all_combos:
        overlap_t1 = len(set(combo).intersection(t1_set))
        if overlap_t1 <= 2:
            base.append(combo)
    if not base:
        base = all_combos
    return base


def select_vortex_sestinas_multi(dodeca_pool, adjusted_scores, history, n_sestinas=2):
    if n_sestinas <= 0:
        return []

    base_combos = _build_candidates(dodeca_pool, adjusted_scores, history)

    # SESTINA 1: REALISTICA
    realistic = []
    for combo in base_combos:
        s = sorted(combo)
        total = sum(s)
        if not (240 <= total <= 310):
            continue
        pari = sum(1 for n in s if n % 2 == 0)
        if pari < 2 or pari > 4:
            continue
        bassi = sum(1 for n in s if n <= 45)
        if bassi < 2 or bassi > 4:
            continue
        decadi = len(set((n - 1) // 10 for n in s))
        if decadi < 4:
            continue
        consecutivi = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
        if consecutivi > 1:
            continue
        realistic.append((combo, _score_realistic(combo, adjusted_scores)))

    realistic.sort(key=lambda x: x[1], reverse=True)
    if realistic:
        sestina1 = list(realistic[0][0])
    else:
        relaxed = [(c, _score_realistic(c, adjusted_scores))
                   for c in base_combos if 220 <= sum(c) <= 320]
        relaxed.sort(key=lambda x: x[1], reverse=True)
        sestina1 = list(relaxed[0][0]) if relaxed else list(base_combos[0])

    selected = [(sestina1, _score_realistic(sestina1, adjusted_scores))]
    selected_sets = [set(sestina1)]

    if n_sestinas == 1:
        return [(tuple(s), sc, anti_crowd_score(s), sc) for s, sc in selected]

    # SESTINA 2: ANTI-CROWD
    assassin = []
    for combo in base_combos:
        overlap_s1 = len(set(combo).intersection(selected_sets[0]))
        if overlap_s1 > 1:
            continue
        s = sorted(combo)
        total = sum(s)
        if not (240 <= total <= 310):
            continue
        if sum(1 for n in s if n > 50) < 2:
            continue
        if sum(1 for n in s if n < 35) < 1:
            continue
        if has_visual_pattern(combo):
            continue
        assassin.append((combo, _score_assassin(combo, adjusted_scores)))

    assassin.sort(key=lambda x: x[1], reverse=True)
    if assassin:
        sestina2 = list(assassin[0][0])
    else:
        relaxed = []
        for combo in base_combos:
            if len(set(combo).intersection(selected_sets[0])) <= 2:
                if 240 <= sum(combo) <= 310:
                    relaxed.append((combo, _score_assassin(combo, adjusted_scores)))
        relaxed.sort(key=lambda x: x[1], reverse=True)
        sestina2 = list(relaxed[0][0]) if relaxed else sestina1

    selected.append((sestina2, _score_assassin(sestina2, adjusted_scores)))
    selected_sets.append(set(sestina2))

    # SESTINE 3+
    for _ in range(2, n_sestinas):
        pool_candidates = []
        for combo in base_combos:
            s = sorted(combo)
            total = sum(s)
            if not (240 <= total <= 310):
                continue
            if has_visual_pattern(combo):
                continue
            max_overlap = max(len(set(combo).intersection(s_set))
                              for s_set in selected_sets)
            if max_overlap > 2:
                continue
            score = (_score_realistic(combo, adjusted_scores)
                     + _score_assassin(combo, adjusted_scores)) / 2
            score += (2 - max_overlap) * 10
            pool_candidates.append((combo, score))

        if not pool_candidates:
            break

        pool_candidates.sort(key=lambda x: x[1], reverse=True)
        new_sestina = list(pool_candidates[0][0])
        new_score = (_score_realistic(new_sestina, adjusted_scores)
                     + _score_assassin(new_sestina, adjusted_scores)) / 2

        selected.append((new_sestina, new_score))
        selected_sets.append(set(new_sestina))

    return [
        (tuple(s), sc, anti_crowd_score(s), sc)
        for s, sc in selected
    ]


def select_vortex_sestinas(dodeca_pool, adjusted_scores, history, top_n=2):
    return select_vortex_sestinas_multi(dodeca_pool, adjusted_scores, history, top_n)
