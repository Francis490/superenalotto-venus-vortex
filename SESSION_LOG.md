# SESSION_LOG — Venus Vortex

> Diario di bordo versionato. Aggiornare a ogni sessione significativa.
> Ultimo aggiornamento: 2026-09-28

### Stato attuale
- Versione bot: v3.3.1
- Database: 363 concorsi (208 del 2025 + 155 del 2026)
- Ultimo concorso elaborato: 155 (26/09/2026)
- Prossimo concorso: 156 (29/09/2026)
- Jackpot corrente: 33.400.000 €
- Personal stats: speso €7,00 / vinto €5,00 / bilancio **−€2,00** / ROI **−28,6%**
- Track record: 7 concorsi completati (+1 in attesa), 3+ punti: 0
- Ultima giocata: [5, 11, 15, 34, 87, 88] (concorso 155)
- Sestina bot attuale: [5, 11, 15, 34, 87, 88] (concorso 156)
- Firma: VX-2026-156-E53F40

### Workflow GitHub attivi
- TITAN Engine Automated Execution (cron Mar/Gio/Ven/Sab)
- Manual Update
- Backtest End-to-End
- Generate PWA Icons
- Build History 2026 (validator)
- Import External History
- Generate Manual PDF

### Lavoro in sospeso
- ~~Setup PWA~~ ✅
- ~~Fix True Mimic~~ ✅
- ~~Aggiornamento rendita~~ ✅
- ~~Rimozione anti-crowd~~ ✅
- Monitoraggio concorsi 156+

### Problemi noti
- `fetch_latest_draw.py` scrape jackpot errato → ignorato (override vince)
- `vortex_opportunity.py` v3.4 senza anti-crowd ✅

---

## 2026-09-19/26 — Cronologia precedente

(Sintesi delle sessioni precedenti — vedi versioni archiviate per dettagli)

- Fix PDF (xhtml2pdf, rimozione @page annidati)
- Setup PWA (manifest, sw.js, icone)
- Pulizia requirements.txt
- Fix True Mimic (range 240-310)
- Fix PWA rebranding (TITAN → Venus Vortex)
- Fix backtest_e2e (sort per data)
- Bump azioni GitHub (v5/v6)
- Fix manual_update (sestine sotto concorso+1)
- Fix track_record (6 punti, notifiche duplicate)
- Analisi data samples
- Rimozione anti-crowd da vortex_opportunity.py (v3.4)

---

## 2026-09-20 — Esito concorso 151

**Estrazione:** `[20, 42, 45, 48, 68, 85]` (jolly 49, superstar 41)
**Sestina:** `[5, 30, 31, 34, 65, 80]` → **0 punti**

---

## 2026-09-22 — Esito concorso 152

**Estrazione:** `[12, 42, 57, 65, 76, 77]` (jolly 21, superstar 54)
**Sestina bot:** `[5, 22, 30, 34, 65, 84]` → **1 punto**
**Note:** Concorso non giocato dall'utente.

---

## 2026-09-24 — Esito concorso 153

**Estrazione:** `[1, 28, 31, 50, 63, 85]` (jolly 86, superstar 48)
**Sestina bot:** `[5, 22, 30, 34, 62, 87]` → **0 punti**
**Note:** Concorso non giocato dall'utente.

---

## 2026-09-25 — Esito concorso 154

**Estrazione:** `[10, 18, 26, 33, 39, 45]` (jolly 89, superstar 48)
**Sestina giocata:** `[4, 5, 22, 49, 79, 87]` → **0 punti**
**Costo:** €1

---

## 2026-09-26 — Esito concorso 155

**Estrazione:** `[52, 54, 55, 64, 68, 78]` (jolly 31, superstar 6)
**Sestina giocata:** `[5, 11, 15, 34, 87, 88]` → **0 punti**
**Costo:** €1
**Note:** Estrazione tutta alta (52-78), sestina troppo bassa.

---

## 2026-09-28 — Preparazione concorso 156

**Estrazione 155:** `[52, 54, 55, 64, 68, 78]`
**Jackpot 156:** €33.400.000
**Sestina bot:** `[5, 11, 15, 34, 87, 88]`
**Firma:** `VX-2026-156-E53F40`
**Budget:** MINIMO (1 sestina, €1,00)
**Estrazione:** Martedì 29/09 ore 20:00

**Nota:** `vortex_opportunity.py` aggiornato a v3.4 (senza anti-crowd).

---

## 2026-09-29 — Esito concorso 156

**Estrazione:** `[16, 26, 28, 30, 43, 72]` (jolly 5, superstar 32)
**Sestina giocata:** `[5, 11, 15, 34, 87, 88]` → **0 punti**
**Costo:** €1

**Note:**
- Il numero **5** è uscito solo come **Jolly** → non valido ai fini del punteggio.
- Estrazione concentrata nella fascia 16-72, sestina concentrata su estremi (5, 87, 88) → zero overlap.
- **Secondo concorso consecutivo a 0 punti** (155, 156).

**🚩 Anomalia rilevata:**
La sestina del 156 (`[5, 11, 15, 34, 87, 88]`) è **identica** a quella del 155. Va verificato se:
- (a) è una scelta deliberata (replay fino a hit), oppure
- (b) è un **bug** del generatore che non ha rigenerato la sestina dopo il concorso 155.
L'anomalia è temporalmente sospetta: `vortex_opportunity.py` è stato modificato a v3.4 (rimozione anti-crowd) il 28/09, cioè **dopo** la giocata 155 e **prima** della 156. Possibile regressione introdotta dal refactor.

**Personal stats aggiornate:**
- Speso: €8,00
- Vinto: €5,00
- Bilancio: **−€3,00**
- ROI: **−37,5%**
- Concorsi completati: 8
- Hit ≥ 3 punti: 0

**Problemi:**
- Sospetto bug generazione sestina (vedi sopra)
- 8 concorsi consecutivi senza hit ≥3 punti (atteso statisticamente ≈1 hit ogni 10-12 giocate)

**Decisioni:**
- Aprire investigazione sul flusso di generazione/persistenza della sestina.
- Verificare `vortex_opportunity.py` v3.4 e workflow TITAN.

**Prossimo:**
- Investigare bug sestina
- Preparare concorso 157 (giovedì 01/10)
- Valutare revisione pesi generatore se il trend 0-hit continua

---

## 2026-09-29 (sera) — Fix sestina duplicata + override consumed

**Obiettivo:** Diagnosticare e risolvere l'anomalia della sestina duplicata
tra concorso 155 e 156.

### Diagnosi

**Root cause identificata:** `true_mimic_generator.generate_mimic_sestinas`
era completamente **deterministico**. Tutte le combo valide hanno score 1.0,
quindi il `sort(key=lambda x: x[1], reverse=True)` era un no-op e veniva
sempre scelta la prima combo in ordine lessicografico del pool. Quando il
pool rimaneva stabile tra due concorsi consecutivi, la sestina risultava
identica.

**Non era** un bug di persistenza. Verificati e scartati:
- ❌ `venus_history.json` non aggiornato → falso, arrivava al 155
- ❌ `next_concorso` sbagliato → falso, era 156
- ❌ `record_predictions` non sovrascrive → falso, funzionava correttamente
- ❌ Rebase git ha perso commit → falso
- ❌ Override non consumato → vero, ma bug collaterale (non causa del duplicato)

**Bug collaterale scoperto:** `venus_manual_override.json` non veniva
consumato dopo l'uso → rimaneva a inquinare la diagnostica delle run future
(es. "override: concorso 155 già presente" ad ogni run).

### Fix applicati

**`true_mimic_generator.py`:**
- Aggiunto parametro `seed` a `generate_mimic_sestinas` e `generate_true_mimic`
- Implementato tie-breaker random deterministico basato su seed:
  `rng = random.Random(seed)` → `rng.random()` come chiave secondaria di sort
- Stesso concorso → stessa sestina (riproducibile). Concorso diverso → sestina diversa.

**`vortex_opportunity.py`:**
- Propagazione parametro `seed` a `select_vortex_sestinas_multi` e `select_vortex_sestinas`
- Passaggio `seed` a `generate_true_mimic`

**`scraper.py`:**
- Passaggio `seed=next_concorso` alla pipeline di generazione sestine
- Nuova funzione `consume_manual_override()`: azzera `last_draw` dopo l'uso
  (mantiene `jackpot` come override permanente)
- Nuova funzione `get_previous_sestina()`: safety net anti-duplicato
- Log esplicito overlap con sestina del concorso precedente

**`venus_sync.yml`:**
- Aggiunto `venus_manual_override.json` alla commit list
- Aggiunto step "Verifica avanzamento history": fail esplicito se l'ultimo
  concorso 2026 in history ha più di 8 giorni (rileva fetch rotto silenzioso)

### Test (run #154 del 29/09)

**Setup:** override manuale con concorso 156, track record ripristinato con
la sestina originale 156 ([5,11,15,34,87,88]).

**Risultato:**
- ✅ `[+] Config: override last_draw presente (concorso 156)`
- ✅ `[+] OVERRIDE: aggiunto concorso 156`
- ✅ `[+] Override consumato: last_draw rimosso`
- ✅ `[+] Ultima estrazione 2026: concorso 156 del 29/09/2026`
- ✅ `Seed (deterministico): 157`
- ✅ `[+] Differenziata da concorso 156 (overlap 3/6)`
- ✅ `[+] Track: concorso 156 -> miglior esito = 0 punti`
- ✅ `[+] Track record: registrato concorso 157 (1 sestine)`
- ✅ `Concorso di riferimento: 157 del 01/10/2026`
- ✅ Nessuna regressione su concorsi 149-155

**Sestina generata per il 157:** nuova (non più [5,11,15,34,87,88]).

### Anomalia residua: `fetch_latest_draw.py`

**Sintomo:** gira per 2m06s e non aggiunge nulla a history. Il concorso 156
è stato aggiunto solo grazie all'override manuale.

**Diagnosi in corso:**
- Riscritto `fetch_latest_draw.py` in versione diagnostica con logging
  pesante (status HTTP, len risposta, sample primi 1500 char per ogni fonte
  e ogni proxy)
- Aggiunto `fetch_debug.log` come output committato dal workflow
- Al prossimo run (giovedì 01/10) il log rivelerà la causa esatta

### Stato attuale

- Versione bot: **v3.4.1** (con seed fix)
- Database: **364 concorsi** (208 del 2025 + 156 del 2026)
- Ultimo concorso elaborato: **156** (29/09/2026)
- Prossimo concorso: **157** (01/10/2026)
- Jackpot corrente: **€33.400.000**
- Personal stats: speso **€8,00** / vinto **€5,00** / bilancio **−€3,00** / ROI **−37,5%**
- Track record: **8 concorsi completati** (+1 in attesa), 3+ punti: **0**
- Ultima giocata: `[5, 11, 15, 34, 87, 88]` (concorso 156, 0 punti)
- Sestina bot attuale: **nuova per il 157** (generata con seed=157)
- Override manuale: **consumato e pulito** ✅

### Lavoro in sospeso

- ~~Fix True Mimic (range 240-310)~~ ✅
- ~~Setup PWA~~ ✅
- ~~Rimozione anti-crowd~~ ✅
- ~~Fix sestina duplicata~~ ✅
- **Debug `fetch_latest_draw.py`** ← prossimo
- Monitoraggio concorsi 157+
- Valutare revisione pesi generatore se trend 0-hit continua

### Problemi noti

- `fetch_latest_draw.py` **completamente rotto** (non aggiunge estrazioni).
  Workaround attuale: override manuale. Versione diagnostica deployata,
  in attesa di log per diagnosi definitiva.
- 8 concorsi consecutivi senza hit ≥3 punti. Atteso statisticamente
  ≈1 hit ogni 10-12 giocate. Non ancora conclusivo ma da monitorare.
