# SESSION_LOG — Venus Vortex

> Diario di bordo versionato. Aggiornare a ogni sessione significativa.
> Ultimo aggiornamento: 2026-09-25

## 2026-09-19 — Ripartenza e creazione diario

### Stato attuale
- Versione bot: v3.3.1
- Database: 362 concorsi (208 del 2025 + 154 del 2026)
- Ultimo concorso elaborato: 153 (24/09/2026)
- Prossimo concorso: 154 (25/09/2026)
- Jackpot corrente: 31.700.000 €
- Personal stats: speso €4,00 / vinto €5,00 / bilancio +€1,00 / ROI +25,00%
- Track record: 5 concorsi completati (+1 in attesa), 3+ punti: 0
- Ultima giocata user: [5, 30, 31, 34, 65, 80] (concorso 151)
- Sestina bot attuale: [4, 5, 22, 49, 79, 87] (concorso 154)
- Firma: VX-2026-154-45B90B
- Concorso: 154

### Workflow GitHub attivi
- TITAN Engine Automated Execution (cron Mar/Gio/Ven/Sab)
- Manual Update
- Backtest End-to-End
- Generate PWA Icons
- Build History 2026 (validator)
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
- build_history_2026.py (validator)
- MANUALE_VENUS_VORTEX.md
- generate_manual_pdf.py

### Lavoro in sospeso
1. ~~Lanciare workflow "Generate Manual PDF" e scaricare il PDF.~~ ✅
2. ~~Riprendere setup PWA: manifest.json, sw.js, icone.~~ ✅
3. ~~Pulire requirements.txt.~~ ✅
4. ~~Rimuovere file diagnostici residui.~~ ✅
5. ~~Valutare fix True Mimic (range 240-310).~~ ✅
6. ~~Analisi Blocco 6: data samples.~~ ✅

### Problemi noti
- `fetch_latest_draw.py` scrape un jackpot errato (119M invece di 31,7M). Ignorato perché l'override manuale vince. Da indagare in futuro.
- Errore Telegram 400 risolto: caption troppo lunga, ora troncata.
- True Mimic: fix applicato e verificato.

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

## 2026-09-19 — Fix PWA: rebranding manifest + service worker

**Obiettivo:** Allineare PWA al brand "Venus Vortex" (era rimasto "TITAN God Mode").

**Fatto:**
- **manifest.json**: rebranding completo (name, short_name, description), colore theme allineato a `#0a0612`, `start_url` a `./`, `purpose` separato in `any`/`maskable`, aggiunto `id` e `categories`.
- **sw.js**: cache rinominata da `titan-cache-v1` a `venus-vortex-cache-v1` con versioning esplicito, aggiunto fallback 503, `event.waitUntil` su cache.put, skip richieste cross-origin e non-GET, aggiunto `favicon.ico`.
- **index.html**: aggiunto `<meta name="mobile-web-app-capable">` (standard W3C), sostituito placeholder bot Telegram con `FrancisenalottoBot`.
- Rimossi da pre-cache `venus_database.json` e `vortex_chart.png` (sono network-first).

**Problemi:**
- Il nome PWA era "TITAN God Mode" (residuo del rebranding a Venus Vortex).
- `theme_color` in manifest (`#09090b`) diverso da quello in `index.html` (`#0a0612`).
- `purpose: "any maskable"` combinato (sconsigliato dallo standard).

**Decisioni:**
- Brand "Venus Vortex" come unico nome in tutta la PWA.
- Palette "spazio" `#0a0612` come theme_color ovunque.

**Prossimo:**
- Blocco 5: workflow GitHub Actions.

---

## 2026-09-19 — Fix backtest_e2e (sort cronologico)

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
- Blocco 5: workflow GitHub Actions.

---

## 2026-09-19 — Fix workflow + manual_update

**Obiettivo:** Aggiornare azioni GitHub deprecate e correggere logica di manual_update.

**Fatto:**
- **venus_sync.yml** e **manual_update.yml**: bump `actions/checkout@v4` → `@v5`, `actions/setup-python@v5` → `@v6`, aggiunto `cache: 'pip'`, aggiunto `timeout-minutes`.
- **manual_update.py**: le sestine giocate ora vengono registrate sotto `concorso + 1` (concorso prossimo) invece che sotto il concorso appena uscito.

**Problemi:**
- Workflow con azioni deprecate (warning Node.js 20).
- Bug logico: le sestine per il concorso 151 venivano registrate sotto il 150.

**Decisioni:**
- Bump azioni per risolvere warning e garantire supporto futuro.
- Le sestine giocate vanno sempre registrate sotto il concorso per cui si giocano (prossimo).

**Prossimo:**
- Correzione dati in `venus_played.json` e `SESSION_LOG.md`.

---

## 2026-09-19 — Correzione dati giocate reali

**Obiettivo:** Allineare `venus_played.json` e `SESSION_LOG.md` con le giocate reali.

**Fatto:**
- Confermato che la sestina `[5, 30, 34, 48, 65, 87]` era per il **concorso 150** (correttamente registrata).
- Aggiunta entry per il **concorso 151** con sestina `[5, 30, 31, 34, 65, 80]`.
- Aggiornato `SESSION_LOG.md`:
  - Personal stats: speso €4,00 (2+1+1) / vinto €5,00 / bilancio +€1,00 / ROI +25,00%.
  - Ultima giocata: `[5, 30, 31, 34, 65, 80]`.

**Problemi:**
- Discrepanza tra SESSION_LOG e played.json.
- Nessun dato storico mancante.

**Decisioni:**
- `venus_played.json` è la fonte di verità per le giocate reali.

**Prossimo:**
- Monitorare l'esito dei concorsi 150 e 151.
- Completare analisi degli altri workflow GitHub (Blocco 5).

---

## 2026-09-19 — Blocco 5: bump azioni GitHub su tutti i workflow

**Obiettivo:** Risolvere il warning "Node.js 20 is deprecated" e modernizzare i workflow.

**Fatto:**
- Bump `actions/checkout@v4` → `@v5` su tutti i workflow.
- Bump `actions/setup-python@v5` → `@v6` su tutti i workflow.
- Aggiunto `cache: 'pip'` dove mancava (installazioni più veloci).
- Aggiunto `timeout-minutes` a tutti i job (evita run appesi).
- Aggiunto `git pull --rebase` prima del push dove mancava (evita conflitti tra workflow concorrenti).
- Workflow aggiornati:
  - `venus_sync.yml` (TITAN)
  - `manual_update.yml`
  - `backtest.yml`
  - `generate_icons.yml`
  - `generate_manual.yml`
  - `build_history.yml`
  - `import_history.yml`

**Problemi:**
- Warning GitHub: "Node.js 20 is deprecated. The following actions target Node.js 20 but are being forced to run on Node.js 24: actions/checkout@v4, actions/setup-python@v5".

**Decisioni:**
- Tutti i workflow usano le stesse versioni di azioni per coerenza e manutenibilità.
- Il pattern comune include: `checkout@v5`, `setup-python@v6` con `cache: 'pip'`, `timeout-minutes`, `git pull --rebase` prima del push.

**Prossimo:**
- Blocco 6: data samples JSON.
- Aggiornare il PDF del manuale quando ci saranno modifiche sostanziali.

---

## 2026-09-19 — Blocco 6: analisi data samples

**Obiettivo:** Verificare coerenza tra strutture JSON e codice.

**Fatto:**
- **venus_played.json**: verificato, coerente. Aggiunta giocata concorso 151.
- **venus_history.json**: analizzato in dettaglio.
  - Totale: **358 entry** (208 del 2025 + 150 del 2026).
  - Tutte le date in formato `DD/MM/YYYY`.
  - Tutte le `combinazione` hanno 6 numeri in range 1-90.
  - Pattern offset +1000 per il 2025 rispettato (1001-1208).
  - Nessun duplicato.
- Identificata **incoerenza SESSION_LOG**: riportava 357 concorsi (208+149) invece di 358 (208+150). Corretto.
- Identificata **entry 150 con campo `sestina` mancante** (le altre 357 ce l'hanno).
- Identificate **divergenze tra `venus_history.json` e `build_history_2026.py`**: alcune entry hardcoded non corrispondono ai dati reali (es. concorso 16, 17, 51, 68). Il merge non sovrascrive, quindi nessun rischio immediato, ma il codice è "stale".

**Problemi:**
- SESSION_LOG riportava 357/149 invece di 358/150.
- Entry 150 manca di `sestina`.
- `build_history_2026.py` ha dati hardcoded divergenti dal JSON (che è la fonte di verità).

**Decisioni:**
- `venus_history.json` è la **fonte di verità** per i dati storici.
- `build_history_2026.py` va reso "validator" più che "seeder": il suo scopo diventa verificare completezza, non iniettare dati potenzialmente stale.
- Fix SESSION_LOG: aggiornati conteggi a 358/150.

**Prossimo:**
- Fix entry 150 (aggiungere `sestina`).
- Refactor `build_history_2026.py` (trust del JSON).

---

## 2026-09-20 — Esito concorso 151

**Fatto:**
- Estrazione: `[20, 42, 45, 48, 68, 85]` (jolly 49, superstar 41)
- Giocata: `[5, 30, 31, 34, 65, 80]` → **0 punti**
- Somma estratti: 308 (dentro range 240-310 ✅)
- Bilancio: +€1,00 (invariato)

**Note:**
- Nessuna vincita, esito statisticamente previsto.
- Bot ha correttamente rilevato il risultato e rigenerato per il 152.

**Prossimo:**
- Concorso 152 (martedì 22/09/2026).

---

## 2026-09-22 — Esito concorso 152

**Fatto:**
- Estrazione: `[12, 42, 57, 65, 76, 77]` (jolly 21, superstar 54)
- Sestina bot: `[5, 22, 30, 34, 65, 84]` → **1 punto**
- Bilancio: +€1,00 (invariato)

**Note:**
- Nessuna vincita (serve 2+ punti).

**Prossimo:**
- Concorso 153 (mercoledì 24/09/2026).

---

## 2026-09-24 — Esito concorso 153

**Fatto:**
- Estrazione: `[1, 28, 31, 50, 63, 85]` (jolly 86, superstar 48)
- Sestina bot: `[5, 22, 30, 34, 62, 87]` → **0 punti**
- Bilancio: +€1,00 (invariato)

**Note:**
- Concorso giocato solo dal bot, non dall'utente (non presente in `venus_played.json`).

**Prossimo:**
- Concorso 154 (venerdì 25/09/2026).

---

## 2026-09-25 — Sestina per concorso 154

**Fatto:**
- Bot ha generato: `[4, 5, 22, 49, 79, 87]` (somma 246, Z -0.62)
- Firma: `VX-2026-154-45B90B`
- Jackpot: €31.700.000
- Budget: MINIMO (1 sestina, €1,00)
- Vortex Numerical Field: `[4, 5, 22, 27, 30, 34, 49, 62, 79, 80, 87, 88]`

**Problemi:**
- Nessuno.

**Prossimo:**
- Attendere esito concorso 154 (25/09/2026).

---

## Template nuova sessione

### YYYY-MM-DD — Titolo
**Obiettivo:**
**Fatto:**
**Problemi:**
**Decisioni:**
**Prossimo:**
