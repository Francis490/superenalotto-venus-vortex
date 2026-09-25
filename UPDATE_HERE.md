# Aggiorna Venus Vortex - Concorso N. 154

> Ultima generazione automatica: **2026-09-25 19:52:27**

---

## Stato attuale

| Campo | Valore |
|---|---|
| **Ultima estrazione** | Concorso N. 153 del 24/09/2026 |
| **Combinazione** | `[1, 28, 31, 50, 63, 85]` |
| **Jolly** | 86 |
| **SuperStar** | 48 |
| **Prossimo concorso** | N. 154 del 25/09/2026 |
| **Jackpot attuale** | EUR 31,700,000 |

---

## Procedura aggiornamento (2 minuti)

### STEP 1 - Trova i numeri veri del concorso 154

Dopo l'estrazione, cerca sul sito ufficiale SuperEnalotto:
- 6 numeri vincenti
- Jolly
- SuperStar

### STEP 2 - Apri il file di override

Link diretto:

```
https://github.com/Francis490/superenalotto-venus-vortex/edit/main/venus_manual_override.json
```

### STEP 3 - Sostituisci il contenuto con questo template

```json
{
  "jackpot": 31700000,
  "last_draw": {
    "concorso": 154,
    "data": "25/09/2026",
    "combinazione": [0, 0, 0, 0, 0, 0],
    "jolly": 0,
    "superstar": 0
  },
  "note": "Compila con i numeri reali del concorso 154"
}
```

**Sostituisci:**
- `[0, 0, 0, 0, 0, 0]` con i 6 numeri veri (ordine crescente)
- `"jolly": 0` con il Jolly vero
- `"superstar": 0` con il SuperStar vero
- `"jackpot": 31700000` con il nuovo jackpot (o lascia invariato)

### STEP 4 - Commit changes

In fondo alla pagina, clicca **Commit changes**.

### STEP 5 - Lancia il workflow

Link diretto:

```
https://github.com/Francis490/superenalotto-venus-vortex/actions/workflows/venus_sync.yml
```

Clicca **Run workflow** -> **main** -> **Run**.

### STEP 6 - Fatto!

Dopo ~60 secondi ricevi il report Telegram con i nuovi dati.

---

## Orari estrazioni SuperEnalotto

| Giorno | Ora |
|---|---|
| Martedi | 20:00 |
| Giovedi | 20:00 |
| Venerdi | 20:00 |
| Sabato | 20:00 |

Aggiorna il file **dopo le 20:30**.

---

*Generato automaticamente da Venus Vortex - Cosmic Pattern Engine*
