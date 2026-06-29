
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

import pandas as pd
import numpy as np

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
        ["AUD/CAD OTC", "AUD/JPY OTC"],
        ["EUR/JPY OTC", "GBP/JPY OTC"],
        ["NZD/USD OTC", "EUR/GBP OTC"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

user_state = {}

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def macd(series):
    ema12 = series.ewm(span=12).mean()
    ema26 = series.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    return macd_line, signal

def bollinger(series):
    sma = series.rolling(20).mean()
    std = series.rolling(20).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    return upper, lower

def get_fake_data():
    prices = np.random.normal(1.10, 0.01, 100)
    return pd.DataFrame({"close": prices})

def analyze(df):
    close = df["close"]

    r = rsi(close).iloc[-1]
    macd_line, signal = macd(close)
    m = macd_line.iloc[-1]
    s = signal.iloc[-1]

    upper, lower = bollinger(close)
    price = close.iloc[-1]

    score = 0
    signals = []

    if r < 30:
        score += 1
        signals.append("RSI survente")
    elif r > 70:
        score -= 1
        signals.append("RSI surachat")

    if m > s:
        score += 1
        signals.append("MACD haussier")
    else:
        score -= 1
        signals.append("MACD baissier")

    if price < lower.iloc[-1]:
        score += 1
        signals.append("Prix sous Bollinger")
    elif price > upper.iloc[-1]:
        score -= 1
        signals.append("Prix au-dessus Bollinger")

    if score >= 2:
        decision = "🟢 BUY"
    elif score <= -2:
        decision = "🔴 SELL"
    else:
        decision = "⚪ NEUTRE"

    return decision, price, r, signals

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot OTC Trading PRO prêt !",
        reply_markup=MENU
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "📈 Nouveau signal":
        await update.message.reply_text("Choisis une durée :", reply_markup=DURATION)

    elif text in ["1 minute", "3 minutes", "5 minutes"]:
        user_state[chat_id] = {"duration": text}
        await update.message.reply_text("Choisis une paire OTC :", reply_markup=OTC)

    elif text == "💱 Paires OTC":
        await update.message.reply_text("Choisis une paire OTC :", reply_markup=OTC)

    elif text.endswith("OTC"):
        df = get_fake_data()
        decision, price, r, signals = analyze(df)

        msg = f"""
📊 PAIRE : {text}
⏱ Durée : {user_state.get(chat_id, {}).get("duration", "N/A")}

💰 Prix : {price:.5f}
📉 RSI : {r:.2f}

🎯 SIGNAL : {decision}

⚡ Signaux :
- """ + "\n- ".join(signals)

        await update.message.reply_text(msg, reply_markup=MENU)

    elif text == "📜 Historique":
        await update.message.reply_text("📜 Historique vide pour l'instant.")

    elif text == "⬅️ Retour":
        await update.message.reply_text("🏠 Menu principal", reply_markup=MENU)

    else:
        await update.message.reply_text("❌ Option inconnue", reply_markup=MENU)

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))

print("✅ Bot OTC PRO lancé...")
app.run_polling()
