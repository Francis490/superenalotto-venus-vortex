# PROJECT_CONTEXT — Venus Vortex

> Scheda di contesto per bootstrap rapido. Incollare questo file
> all'assistente all'inizio di ogni nuova sessione.
> Ultimo aggiornamento: 2026-09-19

---

## 🪐 IDENTITÀ

- **Nome:** Venus Vortex — Cosmic Pattern Engine
- **Tipo:** Sistema di analisi quantitativa per SuperEnalotto
- **Repo:** https://github.com/Francis490/superenalotto-venus-vortex
- **Sito:** https://francis490.github.io/superenalotto-venus-vortex/
- **Bot Telegram:** @FrancisenalottoBot
- **Versione bot:** v3.3.1
- **Autore:** Francis490

## 📌 SCOPO

Non predice i numeri. Ottimizza:
- **Anti-crowd**: gioca numeri impopolari (se vinci, prendi 3-4x)
- **Disciplina**: gioca solo quando l'EV lo giustifica
- **Tracking**: sa cosa hai giocato e come sta andando
- **Trasparenza**: nessuna promessa di vittoria, solo metodo

## 🗄️ DATABASE

- **358 concorsi** (208 del 2025 con offset +1000, 150 del 2026 con range 1-150)
- Ultimo concorso: **150** (18/09/2026)
- Prossimo concorso: **151** (19/09/2026)
- Jackpot corrente: **29.500.000 €**

## 💰 STATO FINANZIARIO

- Speso: €4,00
- Vinto: €5,00
- Bilancio: +€1,00
- ROI: +25,00%
- Ultima giocata: `[5,30,31,34,65,80]` (concorso 151, firma `VX-2026-151-938394`)

## 🧠 ARCHITETTURA

### File principali
| File | Ruolo |
|---|---|
| `scraper.py` | Orchestratore (TITAN Engine) |
| `vortex_opportunity.py` | Algoritmi quantitativi (EV, scoring, budget mode) |
| `true_mimic_generator.py` | 12 fingerprint + range hard somma 240-310 |
| `fetch_latest_draw.py` | Scraping estrazioni + jackpot (proxy multipli) |
| `personal_stats.py` | Statistiche giocate reali utente |
| `venus_track_record.py` | Track record sestine bot |
| `manual_update.py` | Override manuale concorsi |
| `build_history_2026.py` | **Validator** (non inietta dati) |
| `generate_icons.py` | Icone PWA (Pillow) |
| `generate_manual_pdf.py` | Generazione PDF manuale (xhtml2pdf) |

### Pattern chiave
- **Offset +1000 per il 2025** (concorsi 1001-1208) per evitare collisione con il 2026.
- **Range hard somma sestine: 240-310** (True Mimic).
- **`venus_history.json` è la fonte di verità** per lo storico.
- **`venus_manual_override.json` vince su `venus_jackpot.json`**.

### Dipendenze (`requirements.txt`)
