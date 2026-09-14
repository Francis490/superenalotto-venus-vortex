# 📘 Scheda Tecnica — TITAN Engine

**Progetto**: superenalotto-venus-vortex  
**Versione**: 3.0 "God Mode"  
**Data**: 15/09/2026

---

## 1. Panoramica

| Campo | Valore |
|---|---|
| Nome | TITAN Engine — SuperEnalotto Quantitative Dashboard |
| Repository | Francis490/superenalotto-venus-vortex |
| URL pubblico | https://francis490.github.io/superenalotto-venus-vortex |
| Tipo | PWA + Motore analitico Python |
| Linguaggi | Python 51% · HTML 42% · JavaScript 3% |

### Obiettivo
1. Analizza lo storico delle estrazioni SuperEnalotto
2. Genera pronostici statistici (Dodecaedro + 2 Sestine TITAN)
3. Pubblica una dashboard installabile come app
4. Invia notifiche Telegram con grafico
5. Si aggiorna 4 volte a settimana

---

## 2. Architettura

```
GitHub Actions (CRON Mar/Gio/Ven/Sab 20:15 UTC)
    ↓
fetch_latest_draw.py → scrape estrazioni + jackpot
    ↓
scraper.py → elabora + genera database + grafico + Telegram
    ↓
Commit + Push automatico
    ↓
Deploy GitHub Pages
    ↓
Sito aggiornato + PWA online
```

---

## 3. Struttura Repository

```
superenalotto-venus-vortex/
├── .github/workflows/
│   ├── venus_sync.yml
│   └── generate_icons.yml
├── index.html
├── manifest.json
├── sw.js
├── scraper.py
├── fetch_latest_draw.py
├── generate_icons.py
├── requirements.txt
├── venus_history.json
├── venus_database.json
├── venus_jackpot.json
├── venus_manual_override.json
├── vortex_chart.png
├── icon-192.png
├── icon-512.png
└── favicon.ico
```

---

## 4. Componenti Python

### 4.1 scraper.py

Motore analitico principale. Elabora lo storico e genera i pronostici.

**Funzioni principali:**

| Funzione | Ruolo |
|---|---|
| normalize_history() | Parser universale JSON |
| calculate_raw_scores() | Score per ogni numero |
| apply_cooldown_factor() | Penalizza ultimi usciti |
| build_tiered_dodecahedron() | Pool 12 numeri a 4 strati |
| select_titan_sestinas() | 2 sestine ottimali |
| estimate_confidence() | Confidence da z-score |
| calculate_next_draw_date() | Prossima data valida |
| generate_titan_chart() | Grafico Vortex |
| send_telegram_notification() | Notifica foto+caption |
| build_database_payload() | JSON finale |

### 4.2 fetch_latest_draw.py

Prova a scaricare estrazioni + jackpot da siti pubblici.

**Proxy in cascata:** r.jina.ai → allorigins → corsproxy → diretto  
**Fonti:** estrazionedelotto.it, superenalotto.net, lottologia.com

### 4.3 generate_icons.py

Genera icon-192.png, icon-512.png, favicon.ico (una tantum).

---

## 5. Componenti Web

### 5.1 index.html
- Dark theme (#09090b)
- Responsive mobile-first
- Fetch dinamico di venus_database.json
- Auto-refresh ogni 60s
- PWA-ready

### 5.2 manifest.json
Configurazione PWA: nome, icone, tema, display standalone.

### 5.3 sw.js
Service Worker: network-first per JSON/PNG, cache-first per il resto.

---

## 6. Workflow GitHub Actions

### venus_sync.yml

**Trigger:** cron Mar/Gio/Ven/Sab 20:15 UTC + manuale

**Step:**
1. Checkout
2. Setup Python 3.10
3. pip install -r requirements.txt
4. python fetch_latest_draw.py (continue-on-error)
5. python scraper.py
6. Commit + push
7. Preparazione _site
8. Upload artifact
9. Deploy su GitHub Pages

### generate_icons.yml
Workflow manuale per generare icone PWA.

---

## 7. Algoritmi Quantitativi

### Score grezzo
```
raw_score = (freq_score × 0.6) + (delay_score × 0.4)
```

### Cooldown Factor
| Concorso | Moltiplicatore |
|---|---|
| Ultimo | × 0.25 |
| Penultimo | × 0.60 |
| Terzultimo | × 0.85 |

### Dodecaedro a 4 strati
| Strato | Numeri | Criterio |
|---|---|---|
| 1 | 4 | Top score |
| 2 | 4 | Delay medio (5-15) |
| 3 | 2 | Più freddi |
| 4 | 2 | Anti-massa (32-90) |

Totale: 12 numeri

### Filtri Sestine TITAN
- Overlap con ultima estrazione ≤ 2
- Somma tra 200 e 340
- Almeno 2 numeri ≥ 32

### Confidence
```
confidence = max(0, 25 - |z_score| × 5)
```

### Z-Score
```
z_score = (somma - 273) / 43.5
```

---

## 8. Sicurezza & Segreti

**GitHub Secrets:**
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

Impostati in: Settings → Secrets and variables → Actions.

---

## 9. Flusso Dati

```
venus_history.json ─┐
venus_jackpot.json ─┼─→ scraper.py ─→ venus_database.json
venus_manual_override.json ─┘           ─→ vortex_chart.png
```

**Priorità jackpot:**
1. venus_manual_override.json (max)
2. venus_jackpot.json (auto)
3. DEFAULT_JACKPOT (fallback)

---

## 10. Manutenzione

### Settimanale (dopo ogni concorso)
- Aggiorna venus_manual_override.json
- Verifica workflow verde
- Controlla notifica Telegram

### Mensile
- Verifica sito raggiungibile
- Controlla warning workflow

### Semestrale
- Aggiorna dipendenze
- Verifica fonti scraping

---

## 11. Limiti Noti

| Limite | Mitigazione |
|---|---|
| Scraping bloccato da Cloudflare | Override manuale |
| Jackpot non parsabile | Override manuale |
| HTML siti cambia | continue-on-error |
| Node.js 20 deprecato | GitHub aggiorna |

---

## 12. Troubleshooting

| Sintomo | Fix |
|---|---|
| Workflow rosso IndentationError | Indentazione 4 spazi |
| ModuleNotFoundError | Aggiungi a requirements.txt |
| Sito mostra "—" | Controlla console browser |
| Telegram non arriva | Verifica secrets |
| Jackpot statico | Aggiorna override |

---

## 13. Glossario

- **Dodecaedro A.I.**: pool 12 numeri a 4 strati
- **Sestina TITAN**: combinazione ottimale di 6
- **Z-Score**: distanza dalla media
- **Delay**: concorsi dall'ultima uscita
- **Cooldown**: penalizzazione ultimi usciti
- **Anti-massa**: ≥2 numeri ≥32
- **Kelly Model**: gestione rischio
- **Vortex Chart**: grafico 3 pannelli
- **Override**: sostituzione manuale

---

## 14. Riferimenti Tecnici

| Pacchetto | Versione |
|---|---|
| Python | 3.10+ |
| numpy | 1.26.4 |
| scipy | 1.12.0 |
| matplotlib | 3.8.3 |
| Pillow | 10.3.0 |
| requests | 2.32.3 |
| beautifulsoup4 | 4.12.3 |
| GitHub Actions | v4 |
| Node.js | 20 |

---

**Stato**: ✅ Produzione / Stable  
**Versione**: 3.0 "God Mode"  
**Data**: 15/09/2026
