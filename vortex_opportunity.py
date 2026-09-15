"""
vortex_opportunity.py
VENUS VORTEX — Opportunity Engine

Moduli:
1. Anti-Crowd Filter — evita numeri popolari (date, pattern visivi)
2. EV Calculator — calcola l'Expected Value per giocata
3. Rollover Detector — identifica finestre di opportunità
4. Vortex Signature — traccia ogni sestina con ID crittografico
5. Backtest Engine — verifica performance storiche
6. Vortex Optimizer — selezione finale anti-crowd + statistica
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
    # 1-31: date di nascita, giocatissimi
    if 1 <= number <= 31:
        return 0.4
    # 32-45: giorni dei mesi, abbastanza giocati
    elif 32 <= number <= 45:
        return 0.7
    # 46-60: rari
    elif 46 <= number <= 60:
        return 1.2
    # 61-90: molto rari
    elif 61 <= number <= 90:
        return 1.5
    return 1.0


def has_visual_pattern(sestina):
    """Rileva pattern visivi tipici dei giocatori casuali."""
    s = sorted(sestina)

    # Troppi consecutivi (3+)
    consecutivi = sum(1 for i in range(len(s) - 1) if s[i + 1] - s[i] == 1)
    if consecutivi >= 2:
        return True

    # Tutti nella stessa decade o 2 decadi
    decadi = set((n - 1) // 10 for n in s)
    if len(decadi) <= 2:
        return True

    # Tutti multipli di 5 o 10 (pattern schedina)
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
    """
    Stima il numero di giocate totali basato sul jackpot.
    Più il jackpot è alto, più gente gioca.
    """
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
    """
    Calcola l'Expected Value per una giocata da 1€.
    Ritorna dizionario con tutti i dati utili.
    """
    prob_6 = 1 / 622_614_630
    players = estimate_players(jackpot)
    expected_winners = max(1.0, players * prob_6)

    # Con anti-crowd, il jackpot effettivo è moltiplicato
    # perché dividiamo con meno persone
    effective_jackpot = (jackpot / expected_winners) * anti_crowd_factor

    ev_6 = prob_6 * effective_jackpot

    # Contributo stimato degli altri premi (5+1, 5, 4, 3)
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
        return {
            "level": "NORMALE",
            "emoji": "⚪",
            "message": "EV negativo. Gioca il minimo o salta.",
        }
    elif jackpot < 50_000_000:
        return {
            "level": "INTERESSANTE",
            "emoji": "🟡",
            "message": "EV quasi neutro. Puoi giocare 2 sestine.",
        }
    elif jackpot < 70_000_000:
        return {
            "level": "BUONA",
            "emoji": "🟠",
            "message": "EV vicino allo zero. Vale la pena giocare.",
        }
    elif jackpot < 100_000_000:
        return {
            "level": "OTTIMA",
            "emoji": "🔴",
            "message": "EV positivo. Attack mode!",
        }
    else:
        return {
            "level": "ECCEZIONALE",
            "emoji": "🔥",
            "message": "EV molto positivo. Gioca forte!",
        }


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
    """
    Verifica quante volte le sestine attuali avrebbero 'azzeccato'
    almeno 3 numeri nelle ultime last_n estrazioni.
    """
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
        # Baseline teorica: P(3+ per sestina) ~ 0.31%
        results["baseline_expected"] = round(
            (1 / 327 + 1 / 11907 + 1 / 1250230 + 1 / 103769105 + 1 / 622614630)
            * 100, 2
        )
    return results


# ==========================================
# 6. VORTEX OPTIMIZER
# ==========================================
def score_sestina(sestina, adjusted_scores):
    """
    Punteggio finale combinando statistica + anti-crowd.
    """
    stat_score = sum(adjusted_scores.get(n, 0.5) for n in sestina)
    crowd_score = anti_crowd_score(sestina)
    return stat_score * crowd_score


def select_vortex_sestinas(dodeca_pool, adjusted_scores, history, top_n=2):
    """
    Seleziona le N sestine migliori combinando:
    - Filtri statistici (somma, parità, cooldown)
    - Filtri anti-crowd (numeri > 45, no pattern visivi)
    - Massima diversità tra le sestine selezionate
    """
    all_combos = list(itertools.combinations(dodeca_pool, 6))
    t1_set = set(history[-1].get("combinazione", [])) if history else set()

    valid = []
    for combo in all_combos:
        # Filtri statistici
        overlap_t1 = len(set(combo).intersection(t1_set))
        if overlap_t1 > 2:
            continue
        combo_sum = sum(combo)
        if not (200 <= combo_sum <= 340):
            continue
        if len([n for n in combo if n >= 32]) < 2:
            continue

        # Filtri anti-crowd (soft: penalizziamo, non scartiamo)
        crowd = anti_crowd_score(combo)
        if has_visual_pattern(combo):
            crowd *= 0.5  # forte penalità ma non escludiamo

        # Almeno 2 numeri "alti" (>45)
        high_count = sum(1 for n in combo if n >= 46)
        if high_count < 1:
            crowd *= 0.6  # penalità se troppo "basso"

        stat_score = sum(adjusted_scores[n] for n in combo)
        final_score = stat_score * crowd

        valid.append((combo, stat_score, crowd, final_score))

    if not valid:
        # Fallback: rilassa i filtri
        for combo in all_combos:
            stat_score = sum(adjusted_scores[n] for n in combo)
            crowd_score = anti_crowd_score(combo)
            valid.append((combo, stat_score, crowd_score, stat_score * crowd_score))

    valid.sort(key=lambda x: x[3], reverse=True)

    if not valid:
        return []

    # Prendi la prima (miglior punteggio)
    result = [valid[0]]

    # Prendi le successive con overlap minimo
    for item in valid[1:]:
        if len(result) >= top_n:
            break
        # Verifica overlap con tutte le già selezionate
        candidate_set = set(item[0])
        max_overlap = max(
            len(candidate_set.intersection(set(r[0]))) for r in result
        )
        if max_overlap <= 2:
            result.append(item)

    # Se non trovate abbastanza diverse, prendi le migliori successive
    idx = 1
    while len(result) < top_n and idx < len(valid):
        result.append(valid[idx])
        idx += 1

    return result
