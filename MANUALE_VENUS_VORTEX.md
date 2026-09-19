# 📘 MANUALE TECNICO — VENUS VORTEX

**Versione**: 3.3.1
**Data**: 19 Settembre 2026
**Autore**: Francis490
**Licenza**: Uso personale

---

## Indice

1. Panoramica
2. Architettura del sistema
3. Componenti software
4. Algoritmi e logica
5. Flusso dati quotidiano
6. Workflow GitHub Actions
7. Bot Telegram
8. PWA e sito web
9. Manuale d'uso quotidiano
10. Manutenzione
11. Troubleshooting
12. Glossario

---

## 1. Panoramica

### 1.1 Scopo

Venus Vortex è un **sistema di analisi quantitativa** per il SuperEnalotto che:

- Analizza uno storico di **357 estrazioni reali** (208 del 2025 + 149 del 2026)
- Genera **sestine ottimizzate** con criteri statistici e anti-crowd
- Calcola **Expected Value (EV)** per ogni concorso
- Gestisce il **budget dinamico** in base al rollover
- Traccia i **risultati reali** delle giocate dell'utente
- Pubblica una **dashboard web** con grafici e statistiche
- Invia un **report Telegram** ad ogni esecuzione

### 1.2 Filosofia del progetto

Il sistema **non predice** i numeri del SuperEnalotto (matematicamente impossibile). Ottimizza invece:

- **Anti-crowd**: gioca numeri impopolari → se vinci, prendi 3-4x
- **Disciplina**: gioca solo quando l'EV lo giustifica
- **Tracking**: sa cosa hai giocato e come sta andando
- **Trasparenza**: nessuna promessa di vittoria, solo metodo

### 1.3 Architettura di alto livello
