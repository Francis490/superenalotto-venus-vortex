# SESSION_LOG — Venus Vortex

> Diario di bordo versionato. Aggiornare a ogni sessione significativa.
> Ultimo aggiornamento: 2026-09-19

## 2026-09-19 — Ripartenza e creazione diario

### Stato attuale
- Versione bot: v3.3.1
- Database: 357 concorsi (208 del 2025 + 149 del 2026)
- Ultimo concorso elaborato: 150 (18/09/2026)
- Prossimo concorso: 151 (19/09/2026)
- Personal stats: speso €4,00 / vinto €5,00 / bilancio +€1,00 / ROI +25,00%
- Track record: 2 concorsi tracciati (+1 in attesa), 3+ punti: 0
- Ultima giocata: [5, 30, 34, 48, 65, 87]
- Firma: VX-2026-151-9A70A3
- Concorso: 151

### Workflow GitHub attivi
- TITAN Engine Automated Execution (cron Mar/Gio/Ven/Sab)
- Manual Update
- Backtest End-to-End
- Generate PWA Icons
- Build History 2026
- Import External History
- Check History Gaps
- Generate Manual PDF

### File principali nel repo
- scraper.py
- vortex_opportunity.py
- true_mimic_generator.py
- personal_stats.py
- venus_track_record.py
- manual_update.py
- MANUALE_VENUS_VORTEX.md
- generate_manual_pdf.py

### Lavoro in sospeso
1. Lanciare workflow "Generate Manual PDF" e scaricare il PDF.
2. Riprendere setup PWA: manifest.json, sw.js, icone.
3. Pulire requirements.txt: rimuovere requests, bs4, lxml, sklearn se non usati.
4. Rimuovere file diagnostici residui: check_history_gaps.py, check_gaps.yml.
5. Valutare fix True Mimic: produce sestine fuori range 240-310; il fallback classico funziona.

### Problemi noti
- True Mimic: 0/1 sestine nel range 240-310 → fallback classico funziona.
- Errore Telegram 400 risolto: caption troppo lunga, ora troncata.
- File diagnostici "orfani" rimossi.

### Prossimi passi immediati
- [ ] Creare/aggiornare SESSION_LOG.md
- [ ] Lanciare "Generate Manual PDF"
- [ ] Scaricare artifact PDF
- [ ] Aggiornare SESSION_LOG.md con esito
- [ ] Passare a setup PWA

---

## Template nuova sessione

### YYYY-MM-DD — Titolo
**Obiettivo:**
**Fatto:**
**Problemi:**
**Decisioni:**
**Prossimo:**
