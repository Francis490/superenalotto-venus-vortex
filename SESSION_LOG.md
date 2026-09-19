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
- fetch_latest_draw.py
- MANUALE_VENUS_VORTEX.md
- generate_manual_pdf.py

### Lavoro in sospeso
1. ~~Lanciare workflow "Generate Manual PDF" e scaricare il PDF.~~ ✅
2. ~~Riprendere setup PWA: manifest.json, sw.js, icone.~~ ✅ (già presente, verificato)
3. ~~Pulire requirements.txt.~~ ✅ (finalizzato con requests e beautifulsoup4)
4. ~~Rimuovere file diagnostici residui.~~ ✅
5. ~~Valutare fix True Mimic (range 240-310).~~ ✅ (verificato sul campo)

### Problemi noti
- Errore Telegram 400 risolto: caption troppo lunga, ora troncata.
- File diagnostici "orfani" rimossi.
- True Mimic: fix applicato e verificato (sestina somma 269).

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
- Verificato `requirements.txt` iniziale: conteneva solo numpy, scipy, matplotlib, Pillow, markdown, xhtml2pdf.
- Rimossi file diagnostici orfani:
  - `check_history_gaps.py` (nessun import esterno, solo diagnostica su stdout)
  - `.github/workflows/check_gaps.yml` (workflow manuale senza artifact né commit)
- Rimosso `Check History Gaps` dalla lista dei workflow attivi.

**Problemi:**
- ⚠️ La pulizia iniziale è stata fatta **senza verificare tutti i file `.py`** che importavano pacchetti esterni.
- Conseguenza: al primo rilancio del workflow TITAN, `fetch_latest_draw.py` è fallito con `ModuleNotFoundError: requests` (riga 14) e poi `ModuleNotFoundError: bs4` (riga 15).

**Decisioni:**
- `requirements.txt` finalizzato con `requests` e `beautifulsoup4`.
- `lxml` **non necessario**: `fetch_latest_draw.py` usa `BeautifulSoup(content, "html.parser")` (parser built-in).
- Procedura futura: prima di rimuovere pacchetti, cercare gli import in tutto il repo con `grep -rn "^import \|^from " *.py`.

**Prossimo:**
- Rilanciare workflow TITAN e verificare il fix del True Mimic.

---

## 2026-09-19 — Fix True Mimic (range 240-310)

**Obiettivo:** Far rispettare al True Mimic il range di somma 240-310.

**Fatto:**
- Aggiunte costanti `SUM_HARD_MIN=240` e `SUM_HARD_MAX=310` in `true_mimic_generator.py`.
- Modificato check #1 in `validate_sestina`: il range effettivo è ora l'**intersezione** tra il bound statistico (μ±1.5σ) e il bound hard 240-310.
- Migliorato il fallback: filtra le combinazioni per somma 240-310 **prima** di ordinarle per score.
- Aggiunto log del range hard nell'output di `generate_true_mimic` per debug futuro.

**Problemi:**
- In precedenza il range era derivato solo da μ±1.5σ (tipicamente 210-330), permettendo somme fuori target.
- Il fallback ereditava lo stesso problema, restituendo sestine fuori range anche quando non trovava valide.

**Decisioni:**
- Il range 240-310 è un vincolo di dominio SuperEnalotto: prevale sul bound statistico e va imposto hard.

**Prossimo:**
- Verificare l'esecuzione del workflow TITAN e controllare che le sestine prodotte siano nel range 240-310.

---

## 2026-09-19 — Verifica end-to-end TITAN

**Obiettivo:** Verificare che il bot funzioni a regime dopo i fix.

**Fatto:**
- Aggiunti `requests==2.31.0` e `beautifulsoup4==4.12.3` a `requirements.txt` (necessari per `fetch_latest_draw.py`).
- Workflow TITAN completato con successo.
- Report Telegram ricevuto correttamente con tutti i moduli attivi:
  - Opportunity Engine: EV -0.5344 → SALTA
  - Budget Mode: MINIMO · 1 sestina · 1,00 €
  - Track Record: 1 concorso tracciato (+1 in attesa)
  - Statistiche Personali: ROI +150,00%
  - Statistical Tests: χ²=84.3 (p=0.6211), Entropia 99.6%, Autocorr lag-1 = 0.018
  - Vortex Numerical Field: [5, 25, 30, 31, 34, 43, 48, 57, 65, 72, 80, 87]
- Sestina generata: **[5, 30, 34, 48, 65, 87] → somma 269** ✅ in range 240-310.
- Firma: `VX-2026-150-9D1CEE`.
- Grafici (heatmap + distribuzione) inviati correttamente.

**Problemi:**
- Nessuno. Tutti i fix verificati sul campo.

**Decisioni:**
- `requirements.txt` è ora completo e stabile (8 pacchetti).
- Il True Mimic è affidabile: rispetta il range hard ed è sempre in grado di produrre sestine valide.

**Prossimo:**
- Monitorare le prossime giocate reali (concorsi 151+).
- Sostituire il placeholder `IL_TUO_BOT_USERNAME` in `index.html` con l'username reale del bot.
- Aggiornare il PDF del manuale quando ci saranno altre modifiche sostanziali al `MANUALE_VENUS_VORTEX.md`.

---

## ## 2026-09-19 — Fix bug backtest_e2e (sort cronologico)

**Obiettivo:** Correggere il sort di `backtest_e2e.py` che ordinava per `concorso` invece che per data.

**Fatto:**
- Identificato bug: con offset +1000 sui concorsi 2025 (1001-1208), il sort per `concorso` metteva i 2026 (1-148) prima dei 2025. Risultato: test set = 2025, training set = 2026 → backtest cronologicamente invertito.
- Aggiunta funzione `parse_date()` (helper).
- Sostituito sort per `concorso` con sort per `data`.
- Rimosso `baseline_theoretical` mai usato (codice morto).

**Problemi:**
- Il bug era già presente prima; gli altri moduli (`build_history_2026`, `import_external_history`, `scraper`) usavano correttamente il sort per data.

**Decisioni:**
- Il sort cronologico per data è lo standard per tutti i moduli che gestiscono storico misto 2025/2026.

**Prossimo:**
- Blocco 4 (config & docs): manifest.json, sw.js.
