import os
import json
import requests
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot
from telebot import types

# Importazione moduli dallo scraper nativo
from scraper import train_ml_predictive_model, generate_hybrid_predictions

# ---------------------------------------------------------
# HEALTH-CHECK SERVER (PER SBLOCCARE IL PIANO FREE $0 SU RENDER)
# ---------------------------------------------------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Venus Vortex Bot is Active!")

    def log_message(self, format, *args):
        return  # Silenzia i log HTTP standard

def start_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    server.serve_forever()

# ---------------------------------------------------------
# CONFIGURAZIONE AMBIENTE & SICUREZZA
# ---------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Vortex2026Secret")
GITHUB_TOKEN = os.getenv("GH_PAT_TOKEN")

REPO_OWNER = "Francis490"
REPO_NAME = "superenalotto-venus-vortex"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
authenticated_sessions = set()

# ---------------------------------------------------------
# CONTROLLI DI SICUREZZA
# ---------------------------------------------------------
def is_authorized(user_id):
    return user_id == ADMIN_USER_ID

def is_logged_in(user_id):
    return user_id in authenticated_sessions

# ---------------------------------------------------------
# GESTIONE COMANDI
# ---------------------------------------------------------
@bot.message_handler(commands=['start', 'login'])
def handle_start(message):
    user_id = message.from_user.id
    
    if not is_authorized(user_id):
        bot.reply_to(message, "⛔ <b>ACCESSO NEGATO</b>\nQuesto bot è privato.", parse_mode="HTML")
        return

    args = message.text.split()
    if len(args) > 1:
        if args[1] == ADMIN_PASSWORD:
            authenticated_sessions.add(user_id)
            bot.reply_to(message, "🔓 <b>Autenticazione riuscita!</b> Sessione attivata.", parse_mode="HTML")
            send_dashboard(message.chat.id)
            return
        else:
            bot.reply_to(message, "❌ <b>Password errata!</b> Accesso rifiutato.", parse_mode="HTML")
            return

    if is_logged_in(user_id):
        send_dashboard(message.chat.id)
    else:
        bot.reply_to(message, "🔒 <b>SISTEMA BLOCATO</b>\nPer sbloccare la console invia:\n<code>/login TUA_PASSWORD</code>", parse_mode="HTML")

@bot.message_handler(commands=['logout'])
def handle_logout(message):
    if is_authorized(message.from_user.id):
        authenticated_sessions.discard(message.from_user.id)
        bot.reply_to(message, "🔒 <b>Sessione chiusa.</b> Bot bloccato.", parse_mode="HTML")

# ---------------------------------------------------------
# MENÙ INTERATTIVI
# ---------------------------------------------------------
def send_dashboard(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_data = types.InlineKeyboardButton("📊 Ultima Estrazione & Jackpot", callback_data="cmd_latest")
    btn_predict = types.InlineKeyboardButton("🧠 Genera Previsioni Su Misura", callback_data="cmd_select_count")
    btn_sync = types.InlineKeyboardButton("🔄 Avvia Sync GitHub Actions", callback_data="cmd_trigger_sync")
    btn_logout = types.InlineKeyboardButton("🔒 Chiudi Sessione", callback_data="cmd_logout")

    markup.add(btn_data, btn_predict)
    markup.add(btn_sync)
    markup.add(btn_logout)

    bot.send_message(
        chat_id, 
        "⚡ <b>VENUS VORTEX — CONSOLE INTERATTIVA</b> ⚡\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Seleziona un'operazione dal menu sottostante:", 
        reply_markup=markup, 
        parse_mode="HTML"
    )

def send_sestine_selector(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=5)
    buttons = [types.InlineKeyboardButton(f"{i}", callback_data=f"gen_{i}") for i in range(1, 11)]
    
    markup.add(*buttons[:5])
    markup.add(*buttons[5:])
    markup.add(types.InlineKeyboardButton("⬅️ Torna al Menu", callback_data="cmd_back"))

    bot.send_message(
        chat_id,
        "🎯 <b>SELEZIONE PREVISIONI MACHINE LEARNING</b>\n"
        "Quante sestine desideri elaborare per il prossimo concorso? (Scegli da 1 a 10):",
        reply_markup=markup,
        parse_mode="HTML"
    )

# ---------------------------------------------------------
# CALLBACKS PULSANTI
# ---------------------------------------------------------
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if not is_authorized(user_id):
        bot.answer_callback_query(call.id, "⛔ Utente non autorizzato.", show_alert=True)
        return

    if not is_logged_in(user_id):
        bot.answer_callback_query(call.id, "🔒 Sessione scaduta. Effettua il /login.", show_alert=True)
        return

    if call.data == "cmd_select_count":
        bot.answer_callback_query(call.id)
        send_sestine_selector(chat_id)

    elif call.data.startswith("gen_"):
        count = int(call.data.split("_")[1])
        bot.answer_callback_query(call.id, f"Elaborazione di {count} sestine in corso...")
        
        status_msg = bot.send_message(chat_id, f"🧠 <i>Addestramento Random Forest e generazione di <b>{count}</b> sestine in corso...</i>", parse_mode="HTML")
        
        try:
            history_url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/venus_history.json"
            res = requests.get(history_url, timeout=10)
            
            if res.status_code == 200:
                history = res.json()
                ml_probs = train_ml_predictive_model(history)
                predictions = generate_hybrid_predictions(ml_probs, count=count)
                
                text_out = f"⚡ <b>PREVISIONI MACHINE LEARNING ({count} SESTINE)</b> ⚡\n"
                text_out += "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                
                for idx, p in enumerate(predictions, 1):
                    text_out += f"<b>{idx}.</b> <code>{p['sestina']}</code> | Anti-Massa: <b>{p['ev_score']}</b> | Conf: <code>{p['ml_confidence']}</code>\n"
                
                text_out += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
                text_out += "🌐 <i>Filtri applicati: Sum (200-340), Anti-Cluster, High-Number check.</i>"

                bot.delete_message(chat_id, status_msg.message_id)
                bot.send_message(chat_id, text_out, parse_mode="HTML")
            else:
                bot.edit_message_text("❌ Impossibile recuperare lo storico da GitHub.", chat_id, status_msg.message_id)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Errore durante l'elaborazione ML: {e}")

    elif call.data == "cmd_latest":
        bot.answer_callback_query(call.id, "Recupero dati...")
        url = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/main/venus_database.json"
        try:
            res = requests.get(url, timeout=10).json()
            latest = res["latest_draw"]
            quant = res["quant_metrics"]
            
            msg = (
                f"📌 <b>Concorso:</b> {latest['concorso']} ({latest['data']})\n"
                f"🎲 <b>Sestina:</b> <code>{latest['sestina']}</code>\n"
                f"💰 <b>Jackpot:</b> <b>{latest.get('jackpot', 'N/D')}</b>\n"
                f"📊 <b>Somma:</b> <code>{quant['somma']}</code> (Z-Score: <code>{quant['z_score']}</code>)\n"
                f"👁️ <b>Anti-Massa Score:</b> <code>{quant['anti_mass_index']}</code>"
            )
            bot.send_message(chat_id, msg, parse_mode="HTML")
        except Exception as e:
            bot.send_message(chat_id, f"❌ Errore durante la lettura del database: {e}")

    elif call.data == "cmd_trigger_sync":
        bot.answer_callback_query(call.id, "Invio comando a GitHub...")
        if not GITHUB_TOKEN:
            bot.send_message(chat_id, "⚠️ Token GitHub (GH_PAT_TOKEN) non configurato!")
            return

        gh_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/venus_sync.yml/dispatches"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        resp = requests.post(gh_url, headers=headers, json={"ref": "main"})
        if resp.status_code == 204:
            bot.send_message(chat_id, "🚀 <b>Workflow GitHub avviato con successo!</b>\nRiceverai il report automatico non appena completato.", parse_mode="HTML")
        else:
            bot.send_message(chat_id, f"❌ Errore GitHub ({resp.status_code}): {resp.text}")

    elif call.data == "cmd_back":
        bot.answer_callback_query(call.id)
        send_dashboard(chat_id)

    elif call.data == "cmd_logout":
        authenticated_sessions.discard(user_id)
        bot.send_message(chat_id, "🔒 Sessione chiusa correttamente.")

if __name__ == "__main__":
    # Avvio del server HTTP di Health-Check in un thread separato
    threading.Thread(target=start_health_server, daemon=True).start()
    print("[SECURITY] Bot Interattivo avviato e in ascolto 24/7...")
    bot.infinity_polling(skip_pending=True)
