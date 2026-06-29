from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

TOKEN = "VOTRE_TOKEN"

MENU = ReplyKeyboardMarkup(
    [
        ["📈 Nouveau signal"],
        ["📜 Historique"],
        ["💱 Paires OTC"],
    ],
    resize_keyboard=True,
)

DURATION = ReplyKeyboardMarkup(
    [
        ["1 minute", "3 minutes"],
        ["5 minutes"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

OTC = ReplyKeyboardMarkup(
    [
        ["EUR/USD OTC", "GBP/USD OTC"],
        ["USD/JPY OTC", "USD/CHF OTC"],
        ["USD/CAD OTC", "AUD/USD OTC"],
        ["AUD/CAD OTC", "AUD/CHF OTC"],
        ["AUD/JPY OTC", "AUD/NZD OTC"],
        ["CAD/CHF OTC", "CAD/JPY OTC"],
        ["CHF/JPY OTC", "EUR/AUD OTC"],
        ["EUR/CAD OTC", "EUR/CHF OTC"],
        ["EUR/GBP OTC", "EUR/JPY OTC"],
        ["EUR/NZD OTC", "GBP/AUD OTC"],
        ["GBP/CAD OTC", "GBP/CHF OTC"],
        ["GBP/JPY OTC", "GBP/NZD OTC"],
        ["NZD/CAD OTC", "NZD/CHF OTC"],
        ["NZD/JPY OTC", "NZD/USD OTC"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bienvenue sur votre bot de trading !\n\nChoisissez une option :",
        reply_markup=MENU,
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📈 Nouveau signal":
        await update.message.reply_text("⏱ Choisissez une durée :", reply_markup=DURATION)
    elif text in ["1 minute", "3 minutes", "5 minutes"]:
        await update.message.reply_text("🔍 Analyse du marché...\nVeuillez patienter...")
    elif text == "📜 Historique":
        await update.message.reply_text("📜 Aucun historique disponible.")
    elif text == "💱 Paires OTC":
        await update.message.reply_text("Choisissez une paire OTC :", reply_markup=OTC)
    elif text.endswith("OTC"):
        await update.message.reply_text(f"✅ Paire sélectionnée : {text}\n\nCliquez sur « 📈 Nouveau signal » pour continuer.")
    elif text == "⬅️ Retour":
        await update.message.reply_text("🏠 Menu principal", reply_markup=MENU)
    else:
        await update.message.reply_text("❌ Option inconnue.", reply_markup=MENU)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))

print("✅ Bot lancé...")
app.run_polling()
