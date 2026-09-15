"""
vortex_opportunity.py
VENUS VORTEX — Opportunity Engine v3.2

Moduli:
1. Anti-Crowd Filter — evita numeri popolari (date, pattern visivi)
2. EV Calculator — calcola l'Expected Value per giocata
3. Rollover Detector — identifica finestre di opportunità
4. Vortex Signature — traccia ogni sestina con ID crittografico
5. Backtest Engine — verifica performance storiche
6. Doppia Sestina Complementare:
   - Sestina 1 "Realistica": bilanciata, somma 240-310
   - Sestina 2 "Anti-Crowd": numeri alti ma somma 240-310
7. Balance Pool: 4 bassi (1-30) + 4 medi (31-60) + 4 alti (61-90)
"""
import hashlib
import itertools


# ==========================================
# 1. ANTI-CROWD FILTER
# ==========================================
def anti_crowd_weight(number):
    """
    Peso di desiderabilità basato su quanto il crowd gioca un numero.
    Più alto = meno giocato = miglior valore atteso.
    """
    if 1 <= number <= 31:
        return 0.4       # date di nascita, giocatissimi
    elif 32 <= number <= 45:
        return 0.7       # giorni dei mesi
    elif 46 <= number <= 60:
        return 1.2       # rari
    elif 61 <= number <= 90:
        return 1.5       # molto rari
    return 1.0


def has_visual_pattern(sestina):
    """Rileva pattern visivi tipici dei giocatori casuali."""
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
    """Punteggio complessivo anti-crowd per una sestina."""
    weight_sum = sum(anti_crowd_weight(n) for n in sestina)
    pattern_penalty = 0.5 if has_visual_pattern(sestina) else 1.0
    return weight_sum * pattern_penalty


# ==========================================
# 2. EV CALCULATOR
# ==========================================
def estimate_players(jackpot):
    """Stima il numero di giocate totali basato sul jackpot."""
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
    """Calcola l'Expected Value per una giocata da 1€."""
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
    """Classifica il jackpot in zone di opportunità."""
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
# 4. VORTEX SIGNATURE
# ==========================================
def vortex_signature(sestina, concorso, data_str):
    """Genera un ID univoco crittografico per una sestina."""
    payload = f"{concorso}|{data_str}|{'-'.join(map(str, sorted(sestina)))}"
    hash_full = hashlib.sha256(payload.encode()).hexdigest()
    year = data_str[-4:] if len(data_str) >= 4 else "0000"
    return f"VX-{year}-{concorso:03d}-{hash_full[:6].upper()}"


# ==========================================
# 5. BACKTEST ENGINE
# ==========================================
def backtest(history, sestina1, sestina2, last_n=30):
    """Verifica quante volte le sestine attuali avrebbero azzeccato 3+."""
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
# 6. BALANCE POOL (v3.2)
# ==========================================
def balance_pool(dodeca_pool):
    """
    Bilanciamento del pool: 4 bassi (1-30) + 4 medi (31-60) + 4 alti (61-90).
    Se una fascia non ha abbastanza numeri, completa con la più vicina.
    """
    bassi = sorted([n for n in dodeca_pool if 1 <= n <= 30])
    medi = sorted([n for n in dodeca_pool if 31 <= n <= 60])
    alti = sorted([n for n in dodeca_pool if 61 <= n <= 90])

    target = 4
    balanced = []
    balanced.extend(bassi[:target])
    balanced.extend(medi[:target])
    balanced.extend(alti[:target])

    # Se manca qualcosa, completa con i restanti
    if len(balanced) < 12:
        restanti = [n for n in dodeca_pool if n not in balanced]
        restanti.sort()
        balanced.extend(restanti[:12 - len(balanced)])

    return sorted(balanced[:12])


# ==========================================
# 7. DOPPIA SESTINA COMPLEMENTARE (v3.2)
# ==========================================
def _score_realistic(combo, adjusted_scores):
    """Punteggio per sestina 'realistica'."""
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

    final = (stat_score * crowd
             - dist_from_mean * 0.5
             - parity_penalty
             - balance_penalty
             + decades_bonus)
    return final


def _score_assassin(combo, adjusted_scores):
    """
    Punteggio per sestina 'anti-crowd'.
    Premia numeri alti MA con somma contenuta (già garantita dai filtri).
    """
    s = sorted(combo)
    high_count = sum(1 for n in s if n > 55)
    crowd = anti_crowd_score(combo) ** 1.3
    stat_score = sum(adjusted_scores[n] for n in combo)
    high_bonus = high_count * 12

    final = stat_score * crowd + high_bonus
    return final


def select_vortex_sestinas(dodeca_pool, adjusted_scores, history, top_n=2):
    """
    DOPPIA SESTINA COMPLEMENTARE v3.2
    - Sestina 1: realistica (somma 240-310, bilanciata)
    - Sestina 2: anti-crowd (somma 240-310, con numeri alti ma plausibile)
    """
    all_combos = list(itertools.combinations(dodeca_pool, 6))
    t1_set = set(history[-1].get("combinazione", [])) if history else set()

    # Filtro base: overlap con ultima estrazione
    base_combos = []
    for combo in all_combos:
        overlap_t1 = len(set(combo).intersection(t1_set))
        if overlap_t1 <= 2:
            base_combos.append(combo)
    if not base_combos:
        base_combos = all_combos

    # ==========================================
    # SESTINA 1: REALISTICA (somma 240-310)
    # ==========================================
    realistic_candidates = []
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

        score = _score_realistic(combo, adjusted_scores)
        realistic_candidates.append((combo, score))

    realistic_candidates.sort(key=lambda x: x[1], reverse=True)

    if realistic_candidates:
        sestina1 = list(realistic_candidates[0][0])
    else:
        relaxed = []
        for combo in base_combos:
            total = sum(combo)
            if 220 <= total <= 320:
                relaxed.append((combo, _score_realistic(combo, adjusted_scores)))
        relaxed.sort(key=lambda x: x[1], reverse=True)
        sestina1 = list(relaxed[0][0]) if relaxed else list(base_combos[0])

    # ==========================================
    # SESTINA 2: ANTI-CROWD (somma 240-310)
    # ==========================================
    s1_set = set(sestina1)
    assassin_candidates = []
    for combo in base_combos:
        overlap_s1 = len(set(combo).intersection(s1_set))
        if overlap_s1 > 1:
            continue

        s = sorted(combo)
        total = sum(s)

        # Range somma OBBLIGATORIO 240-310
        if not (240 <= total <= 310):
            continue

        # Almeno 2 numeri > 50 (anima anti-crowd)
        if sum(1 for n in s if n > 50) < 2:
            continue

        # Almeno 1 numero < 35 (per non avere "tutti alti")
        if sum(1 for n in s if n < 35) < 1:
            continue

        # No pattern visivi
        if has_visual_pattern(combo):
            continue

        score = _score_assassin(combo, adjusted_scores)
        assassin_candidates.append((combo, score))

    assassin_candidates.sort(key=lambda x: x[1], reverse=True)

    if assassin_candidates:
        sestina2 = list(assassin_candidates[0][0])
    else:
        relaxed = []
        for combo in base_combos:
            overlap_s1 = len(set(combo).intersection(s1_set))
            if overlap_s1 <= 2:
                total = sum(combo)
                if 240 <= total <= 310:
                    relaxed.append((combo, _score_assassin(combo, adjusted_scores)))
        relaxed.sort(key=lambda x: x[1], reverse=True)
        sestina2 = list(relaxed[0][0]) if relaxed else sestina1

    # ==========================================
    # OUTPUT
    # ==========================================
    score1 = _score_realistic(sestina1, adjusted_scores)
    score2 = _score_assassin(sestina2, adjusted_scores)
    crowd1 = anti_crowd_score(sestina1)
    crowd2 = anti_crowd_score(sestina2)

    return [
        (tuple(sestina1), score1, crowd1, score1),
        (tuple(sestina2), score2, crowd2, score2),
    ]
