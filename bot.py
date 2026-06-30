import os
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
import yfinance as yf

TOKEN = os.environ.get("TELEGRAM_TOKEN")

# ---------------- MENU ----------------

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
        ["EUR/JPY OTC", "GBP/JPY OTC"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

user_state = {}

# ---------------- INDICATEURS ----------------

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


def ema_trend(close):
    ema50 = close.ewm(span=50).mean()
    ema200 = close.ewm(span=200).mean()
    if ema50.iloc[-1] > ema200.iloc[-1]:
        return "UP"
    elif ema50.iloc[-1] < ema200.iloc[-1]:
        return "DOWN"
    return "SIDE"


# ---------------- DONNÉES RÉELLES ----------------

def get_real_data(symbol="EURUSD=X"):
    data = yf.download(symbol, period="5d", interval="15m", auto_adjust=True, progress=False)
    data = data.dropna()
    return data


# ---------------- ANALYSE ----------------

def analyze(df):
    close = df["Close"].squeeze()

    r = rsi(close).iloc[-1]
    macd_line, signal = macd(close)
    m = macd_line.iloc[-1]
    s = signal.iloc[-1]

    upper, lower = bollinger(close)
    price = close.iloc[-1]

    trend = ema_trend(close)

    score = 0
    signals = []

    if trend == "UP":
        score += 1
        signals.append("Tendance HAUSSIÈRE (EMA 50 > 200)")
    elif trend == "DOWN":
        score -= 1
        signals.append("Tendance BAISSIÈRE (EMA 50 < 200)")

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

    if score >= 3 and trend == "UP":
        decision = "🟢 STRONG BUY"
    elif score <= -3 and trend == "DOWN":
        decision = "🔴 STRONG SELL"
    else:
        decision = "⚪ NO TRADE"

    return decision, price, r, signals


# ---------------- MAP OTC → SYMBOL ----------------

symbol_map = {
    "EUR/USD OTC": "EURUSD=X",
    "GBP/USD OTC": "GBPUSD=X",
    "USD/JPY OTC": "JPY=X",
    "USD/CHF OTC": "CHF=X",
    "USD/CAD OTC": "CAD=X",
    "AUD/USD OTC": "AUDUSD=X",
    "EUR/JPY OTC": "EURJPY=X",
    "GBP/JPY OTC": "GBPJPY=X",
}


# ---------------- HANDLERS ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Bot Trading PRO (Signaux Réels) prêt !",
        reply_markup=MENU
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "📈 Nouveau signal":
        await update.message.reply_text("Choisis une durée :", reply_markup=DURATION)

    elif text in ["1 minute", "3 minutes", "5 minutes"]:
        user_state[chat_id] = {"duration": text}
        await update.message.reply_text("Choisis une paire :", reply_markup=OTC)

    elif text == "💱 Paires OTC":
        await update.message.reply_text("Choisis une paire :", reply_markup=OTC)

    elif text in symbol_map:
        symbol = symbol_map[text]
        await update.message.reply_text("⏳ Analyse en cours...")

        try:
            df = get_real_data(symbol)

            if df.empty:
                await update.message.reply_text("❌ Pas de données disponibles", reply_markup=MENU)
                return

            decision, price, r, signals = analyze(df)

            msg = (
                f"📊 PAIRE : {text}\n"
                f"⏱ Durée : {user_state.get(chat_id, {}).get('duration', 'N/A')}\n\n"
                f"💰 Prix : {float(price):.5f}\n"
                f"📉 RSI : {float(r):.2f}\n\n"
                f"🎯 SIGNAL : {decision}\n\n"
                f"⚡ ANALYSE :\n- " + "\n- ".join(signals)
            )

            await update.message.reply_text(msg, reply_markup=MENU)

        except Exception as e:
            await update.message.reply_text(f"❌ Erreur : {str(e)}", reply_markup=MENU)

    elif text == "📜 Historique":
        await update.message.reply_text("📜 Historique vide pour l'instant.", reply_markup=MENU)

    elif text == "⬅️ Retour":
        await update.message.reply_text("🏠 Menu principal", reply_markup=MENU)

    else:
        await update.message.reply_text("❌ Option inconnue", reply_markup=MENU)


# ---------------- MAIN ----------------

def main():
    if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))
    print("✅ Bot Trading PRO (REAL DATA) lancé...")
    app.run_polling()


if __name__ == "__main__":
    main()
