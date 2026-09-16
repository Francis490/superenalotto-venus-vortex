"""
vortex_analytics.py
Modulo analytics per Venus Vortex:
- Heatmap numeri caldi/freddi
- Test statistici formali (chi-quadro, entropia, autocorrelazione)
"""
import os
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import chisquare

HEATMAP_FILE = "vortex_heatmap.png"


def generate_heatmap(history, output_path=HEATMAP_FILE):
    """Genera heatmap 9x10 con frequenza di ogni numero 1-90."""
    if not history:
        return None

    freq = {i: 0 for i in range(1, 91)}
    for draw in history:
        for n in draw.get("combinazione", []):
            if 1 <= n <= 90:
                freq[n] += 1

    total_draws = len(history)
    expected = total_draws * 6 / 90 if total_draws > 0 else 1
    ratio = {n: freq[n] / expected for n in range(1, 91)}

    matrix = np.zeros((9, 10))
    labels = np.zeros((9, 10), dtype=int)
    for n in range(1, 91):
        row = (n - 1) // 10
        col = (n - 1) % 10
        matrix[row, col] = ratio[n]
        labels[row, col] = n

    plt.rcParams['text.color'] = '#f1e8ff'
    plt.rcParams['axes.labelcolor'] = '#f1e8ff'

    fig, ax = plt.subplots(figsize=(14, 9), facecolor='#0a0612')
    ax.set_facecolor('#150b1f')

    vmax = max(2.0, float(np.max(matrix)))
    im = ax.imshow(matrix, cmap='RdYlBu_r', vmin=0, vmax=vmax, aspect='equal')

    for i in range(9):
        for j in range(10):
            n = labels[i, j]
            f = freq[n]
            color = "black" if 0.4 < matrix[i, j] / vmax < 0.7 else "white"
            ax.text(j, i, f"{n}\n{f}", ha="center", va="center",
                    color=color, fontsize=10, fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("VORTEX HEATMAP - Frequenze numeri 1-90",
                 fontsize=14, fontweight='bold', color='#06b6d4', pad=15)

    cbar = plt.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Caldo / Freddo", color='#f1e8ff', fontsize=10)
    cbar.ax.yaxis.set_tick_params(color='#f1e8ff')
    plt.setp(plt.getp(cbar.ax.axes, 'yticklabels'), color='#f1e8ff')

    plt.tight_layout()
    plt.savefig(output_path, dpi=200, facecolor=fig.get_facecolor(),
                edgecolor='none')
    plt.close()

    print(f"[+] Heatmap salvata: {output_path}")
    return output_path


def run_statistical_tests(history):
    """Esegue test statistici formali sullo storico estrazioni."""
    if not history or len(history) < 10:
        return None

    results = {}

    freq = {i: 0 for i in range(1, 91)}
    for draw in history:
        for n in draw.get("combinazione", []):
            if 1 <= n <= 90:
                freq[n] += 1

    observed = np.array([freq[n] for n in range(1, 91)])
    expected_arr = np.full(90, len(history) * 6 / 90)

    try:
        chi2, p_value = chisquare(observed, f_exp=expected_arr)
        results["chi_square"] = {
            "value": round(float(chi2), 2),
            "p_value": round(float(p_value), 4),
            "uniform": bool(p_value > 0.05),
        }
    except Exception as e:
        results["chi_square"] = {"error": str(e)}

    total = sum(freq.values())
    if total > 0:
        probs = np.array([freq[n] / total for n in range(1, 91)])
        probs = probs[probs > 0]
        entropy = -np.sum(probs * np.log2(probs))
        max_entropy = math.log2(90)
        results["entropy"] = {
            "value": round(float(entropy), 4),
            "max": round(float(max_entropy), 4),
            "ratio": round(float(entropy / max_entropy), 4),
        }

    sums = [sum(d.get("combinazione", [])) for d in history
            if d.get("combinazione")]
    if len(sums) > 3:
        arr = np.array(sums)
        mean = arr.mean()
        num = np.sum((arr[:-1] - mean) * (arr[1:] - mean))
        den = np.sum((arr - mean) ** 2)
        autocorr = float(num / den) if den != 0 else 0.0
        results["autocorrelation"] = {
            "value": round(autocorr, 4),
            "interpretation": (
                "indipendente" if abs(autocorr) < 0.15 else
                "leggermente correlato" if abs(autocorr) < 0.3 else
                "correlato"
            ),
        }

    if sums:
        results["sums"] = {
            "mean": round(float(np.mean(sums)), 2),
            "std": round(float(np.std(sums)), 2),
            "theoretical_mean": 273.0,
            "theoretical_std": 43.5,
        }

    return results


def format_stats_for_report(stats):
    """Formatta i risultati statistici per il report Telegram."""
    if not stats:
        return "—"

    lines = []

    cs = stats.get("chi_square", {})
    if "p_value" in cs:
        emoji = "✅" if cs.get("uniform") else "⚠️"
        lines.append(f"{emoji} Chi² = {cs['value']} · p = {cs['p_value']}")

    ent = stats.get("entropy", {})
    if "ratio" in ent:
        lines.append(f"📊 Entropia = {ent['ratio'] * 100:.1f}% del massimo")

    ac = stats.get("autocorrelation", {})
    if "value" in ac:
        lines.append(f"🔗 Autocorr lag-1 = {ac['value']} ({ac['interpretation']})")

    su = stats.get("sums", {})
    if "mean" in su:
        lines.append(f"📈 Somma media = {su['mean']} (attesa 273)")

    return "\n".join(lines) if lines else "—"
