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
1. ~~Lanciare workflow "Generate Manual PDF" e scaricare il PDF.~~ ✅
2. ~~Riprendere setup PWA: manifest.json, sw.js, icone.~~ ✅ (già presente, verificato)
3. ~~Pulire requirements.txt.~~ ✅ (già pulito, 6 pacchetti tutti necessari)
4. ~~Rimuovere file diagnostici residui.~~ ✅
5. Valutare fix True Mimic: produce sestine fuori range 240-310; il fallback classico funziona.

### Problemi noti
- True Mimic: 0/1 sestine nel range 240-310 → fallback classico funziona.
- Errore Telegram 400 risolto: caption troppo lunga, ora troncata.
- File diagnostici "orfani" rimossi.

---

## 2026-09-19 — Fix generazione PDF

**Obiettivo:** Risolvere errore `CSSParseError` nel workflow `Generate Manual PDF`.

**Fatto:**
- Lanciato il workflow `Generate Manual PDF` → fallisce con `CSSParseError: Declaration group closing '}' not found`.
- Analizzato il traceback: il parser CSS di `xhtml2pdf` si blocca sul blocco `@page`.
- Identificata la causa: `xhtml2pdf` non supporta le regole annidate dentro `@page`, ovvero i margin box `@bottom-center` e `@bottom-right` usati per footer e numero di pagina.
- Modificato `generate_manual_pdf.py`: rimosse le regole annidate dentro `@page`, mantenendo solo `size` e `margin`.
- Rilanciato il workflow → PDF generato correttamente.

**Problemi:**
- Perdita del piè di pagina con "Venus Vortex — Manuale Tecnico v3.3.1" e numero di pagina.
- `xhtml2pdf` supporta un sottoinsieme limitato di CSS e non gestisce i margin box.

**Decisioni:**
- Si accetta per ora la perdita del piè di pagina: la soluzione rapida sblocca il workflow.
- In futuro, se il footer diventa necessario, si valuterà il passaggio a **WeasyPrint** (supporta nativamente `@page` con margin box e CSS3).

**Prossimo:**
- Scaricare il PDF dall'artifact del workflow.
- Procedere con il setup PWA (`manifest.json`, `sw.js`, icone).

---

## 2026-09-19 — PDF risolto definitivamente

**Obiettivo:** Ottenere un PDF impaginato correttamente (copertina su una pagina, heading renderizzati).

**Fatto:**
- Provato `baileyjm02/markdown-to-pdf` come alternativa → fallito per permessi Docker (`Cannot move outside of directory /github/workspace/`).
- Ripristinato `xhtml2pdf` con `generate_manual_pdf.py` ottimizzato.
- Rimosse le estensioni `toc` e `nl2br`: erano la causa dei titoli Markdown non renderizzati come heading.
- Ridotta altezza copertina (`padding-top: 180` → `60`) e font ridotti: ora la copertina sta su una sola pagina.
- Workflow completato con successo (56s). Artifact `manuale-venus-vortex` caricato.
- Verificato il PDF: copertina su una pagina, indice e heading corretti.

**Problemi:**
- Nessuno.

**Decisioni:**
- `xhtml2pdf` è la soluzione stabile per questo progetto. Nessuna dipendenza da azioni di terze parti.
- `baileyjm02/markdown-to-pdf` scartato (problemi di permessi Docker).

**Prossimo:**
- Pulizia `requirements.txt`.
- Rimozione file diagnostici residui (`check_history_gaps.py`, `check_gaps.yml`).
- Valutazione fix True Mimic (range 240-310).

---

## 2026-09-19 — Pulizia requirements.txt e file diagnostici

**Obiettivo:** Ripulire il repository da dipendenze e file non più necessari.

**Fatto:**
- Verificato `requirements.txt`: già pulito, nessuna dipendenza obsoleta (`requests`, `bs4`, `lxml`, `sklearn` già assenti). File composto da 6 pacchetti tutti necessari:
  - `numpy`, `scipy` → calcoli numerici e statistici
  - `matplotlib` → generazione grafici
  - `Pillow` → generazione icone PWA
  - `markdown`, `xhtml2pdf` → generazione manuale PDF
- Rimossi file diagnostici orfani:
  - `check_history_gaps.py` (nessun import esterno, solo diagnostica su stdout)
  - `.github/workflows/check_gaps.yml` (workflow manuale senza artifact né commit)

**Problemi:**
- Nessuno.

**Decisioni:**
- `requirements.txt` non necessita modifiche.
- Nessun altro file diagnostico residuo rilevato.

**Prossimo:**
- Valutazione fix True Mimic (range 240-310).

---

## Template nuova sessione

### YYYY-MM-DD — Titolo
**Obiettivo:**
**Fatto:**
**Problemi:**
**Decisioni:**
**Prossimo:**
