"""
Bot Telegram d'analyse technique (RSI + MACD + Bollinger Bands)
- Actions via Yahoo Finance (yfinance)
- Crypto via Binance public API (ccxt)

Ce bot ne passe AUCUN ordre. Il analyse et envoie des signaux informatifs.
Ce n'est pas un conseil financier - les signaux techniques peuvent se tromper.
"""

import os
import logging
import asyncio
import base64
from datetime import datetime

import pandas as pd
import numpy as np
import yfinance as yf
import ccxt
import requests

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "PASTE_YOUR_TOKEN_HERE")
CHAT_ID = os.environ.get("CHAT_ID", "PASTE_YOUR_CHAT_ID_HERE")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Liste des actifs surveillés en continu (modifiable)
STOCK_WATCHLIST = ["AAPL", "TSLA", "MSFT"]       # tickers Yahoo Finance
CRYPTO_WATCHLIST = ["BTC/USDT", "ETH/USDT"]       # paires Binance

CHECK_INTERVAL_SECONDS = 60 * 30  # vérifie toutes les 30 minutes

# ---------------------------------------------------------------------------
# MENUS À BOUTONS
# ---------------------------------------------------------------------------
# Durées réalistes uniquement : sur 1-5 min, aucun indicateur technique
# (RSI/MACD/Bollinger) n'a de valeur prédictive fiable. On ne propose donc
# que des échelles où l'analyse a un sens réel.

MENU = ReplyKeyboardMarkup(
    [
        ["📈 Nouveau signal"],
        ["📋 Watchlist"],
    ],
    resize_keyboard=True,
)

DURATION_MENU = ReplyKeyboardMarkup(
    [
        ["1 heure", "4 heures"],
        ["1 jour"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

PAIRS_MENU = ReplyKeyboardMarkup(
    [
        ["BTC/USDT", "ETH/USDT"],
        ["AAPL", "TSLA", "MSFT"],
        ["⬅️ Retour"],
    ],
    resize_keyboard=True,
)

# Correspondance durée affichée -> (timeframe ccxt, interval yfinance, période yfinance)
DURATION_MAP = {
    "1 heure": {"crypto_tf": "1h", "stock_interval": "1h", "stock_period": "1mo"},
    "4 heures": {"crypto_tf": "4h", "stock_interval": "1h", "stock_period": "3mo"},
    "1 jour": {"crypto_tf": "1d", "stock_interval": "1d", "stock_period": "6mo"},
}

CRYPTO_PAIRS = {"BTC/USDT", "ETH/USDT"}
STOCK_PAIRS = {"AAPL", "TSLA", "MSFT"}

# Stocke temporairement la sélection en cours de chaque utilisateur (par chat_id)
user_state = {}

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

crypto_exchange = ccxt.kraken()


# ---------------------------------------------------------------------------
# RÉCUPÉRATION DES DONNÉES
# ---------------------------------------------------------------------------

def get_stock_data(ticker: str, period="6mo", interval="1d") -> pd.DataFrame:
    # yfinance peut parfois renvoyer un DataFrame vide à cause de limitations
    # réseau sur certains hébergeurs cloud. On retente une fois avec un léger délai.
    for attempt in range(2):
        try:
            df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=True)
            if not df.empty:
                # yfinance peut retourner des colonnes multi-niveaux (MultiIndex) selon la version
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.rename(columns=str.lower)
                return df
        except Exception as e:
            logger.warning(f"Tentative {attempt+1} échouée pour {ticker}: {e}")
        if attempt == 0:
            import time
            time.sleep(2)
    return pd.DataFrame()


def get_crypto_data(symbol: str, timeframe="1h", limit=200) -> pd.DataFrame:
    # Kraken utilise le même format "BTC/USDT" via ccxt (conversion automatique en interne)
    ohlcv = crypto_exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


# ---------------------------------------------------------------------------
# INDICATEURS TECHNIQUES
# ---------------------------------------------------------------------------

def compute_rsi(series: pd.Series, period=14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger(series: pd.Series, period=20, num_std=2):
    sma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    return upper, sma, lower


def analyze(df: pd.DataFrame) -> dict:
    """Calcule tous les indicateurs et retourne un résumé + signal."""
    close = df["close"]

    rsi = compute_rsi(close)
    macd_line, signal_line, hist = compute_macd(close)
    upper, mid, lower = compute_bollinger(close)

    last_close = close.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal_line.iloc[-1]
    last_hist = hist.iloc[-1]
    prev_hist = hist.iloc[-2]
    last_upper = upper.iloc[-1]
    last_lower = lower.iloc[-1]

    signals = []
    score = 0  # positif = penche vers achat, négatif = penche vers vente

    # RSI
    if last_rsi < 30:
        signals.append("RSI en survente (<30)")
        score += 1
    elif last_rsi > 70:
        signals.append("RSI en surachat (>70)")
        score -= 1

    # MACD croisement
    if prev_hist < 0 and last_hist > 0:
        signals.append("MACD croise au-dessus du signal (haussier)")
        score += 1
    elif prev_hist > 0 and last_hist < 0:
        signals.append("MACD croise en-dessous du signal (baissier)")
        score -= 1

    # Bollinger
    if last_close <= last_lower:
        signals.append("Prix sous la bande basse de Bollinger")
        score += 1
    elif last_close >= last_upper:
        signals.append("Prix au-dessus de la bande haute de Bollinger")
        score -= 1

    # Recommandation indicative basée sur le score combiné des 3 indicateurs.
    # Ceci reste une lecture purement technique, pas une certitude de marché.
    if score >= 2:
        recommendation = "BUY"
    elif score <= -2:
        recommendation = "SELL"
    else:
        recommendation = "NEUTRE"

    return {
        "price": last_close,
        "rsi": last_rsi,
        "macd": last_macd,
        "macd_signal": last_signal,
        "bollinger_upper": last_upper,
        "bollinger_lower": last_lower,
        "signals": signals,
        "score": score,
        "recommendation": recommendation,
    }


def format_analysis(name: str, result: dict) -> str:
    emoji_map = {"BUY": "🟢", "SELL": "🔴", "NEUTRE": "⚪"}
    rec = result["recommendation"]
    lines = [f"📊 *{name}*"]
    lines.append(f"{emoji_map[rec]} *Recommandation: {rec}*")
    lines.append(f"Prix: {result['price']:.2f}")
    lines.append(f"RSI: {result['rsi']:.1f}")
    lines.append(f"MACD: {result['macd']:.3f} / Signal: {result['macd_signal']:.3f}")
    lines.append(f"Bollinger: [{result['bollinger_lower']:.2f} - {result['bollinger_upper']:.2f}]")

    if result["signals"]:
        lines.append("\n⚡ *Signaux détectés:*")
        for s in result["signals"]:
            lines.append(f"• {s}")
    else:
        lines.append("\nAucun signal fort détecté.")

    lines.append("\n_⚠️ Lecture technique automatisée, pas un conseil financier. À toi de décider._")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ANALYSE D'IMAGE (Gemini Vision - niveau gratuit)
# ---------------------------------------------------------------------------

GEMINI_PROMPT = """Tu analyses une capture d'écran de graphique de trading (bougies, indicateurs visibles).
Réponds en français, de façon concise, avec ce format exact :

RECOMMANDATION: [BUY/SELL/NEUTRE]
RAISON: [2-3 phrases max expliquant ce que tu observes sur le graphique - tendance, niveaux, motifs de bougies]
CONFIANCE: [FAIBLE/MOYENNE/ÉLEVÉE]

Sois honnête sur l'incertitude. Une lecture de graphique reste une estimation, pas une certitude.
Si l'image n'est pas un graphique de trading lisible, dis-le clairement plutôt que d'inventer une réponse."""


def analyze_chart_image(image_bytes: bytes) -> str:
    """Envoie l'image à l'API Gemini (niveau gratuit) et retourne l'analyse texte."""
    if not GEMINI_API_KEY:
        return "⚠️ Aucune clé GEMINI_API_KEY configurée. Ajoute-la dans les variables Railway."

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": GEMINI_PROMPT},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
                ]
            }
        ]
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        logger.error(f"Réponse Gemini inattendue: {data}")
        return "Erreur: réponse inattendue de l'IA d'analyse d'image."


# ---------------------------------------------------------------------------
# COMMANDES TELEGRAM
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Bot d'analyse technique prêt.\n\n"
        "Utilise les boutons ci-dessous, ou les commandes:\n"
        "/signal AAPL — analyse une action\n"
        "/cryptosignal BTC/USDT — analyse une crypto\n"
        "/watchlist — affiche la liste surveillée\n\n"
        "📷 Tu peux aussi m'envoyer directement une photo d'un graphique.\n\n"
        "⚠️ Ceci n'est pas un conseil financier.",
        reply_markup=MENU,
    )


async def signal_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Utilisation: /signal AAPL")
        return
    ticker = context.args[0].upper()
    await update.message.reply_text(f"Analyse de {ticker} en cours...")
    try:
        df = get_stock_data(ticker)
        if df.empty:
            await update.message.reply_text(f"Aucune donnée trouvée pour {ticker}.")
            return
        result = analyze(df)
        await update.message.reply_markdown(format_analysis(ticker, result))
    except Exception as e:
        logger.exception("Erreur signal_stock")
        await update.message.reply_text(f"Erreur lors de l'analyse: {e}")


async def signal_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Utilisation: /cryptosignal BTC/USDT")
        return
    symbol = context.args[0].upper()
    await update.message.reply_text(f"Analyse de {symbol} en cours...")
    try:
        df = get_crypto_data(symbol)
        if df.empty:
            await update.message.reply_text(f"Aucune donnée trouvée pour {symbol}.")
            return
        result = analyze(df)
        await update.message.reply_markdown(format_analysis(symbol, result))
    except Exception as e:
        logger.exception("Erreur signal_crypto")
        await update.message.reply_text(f"Erreur lors de l'analyse: {e}")


async def watchlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "📋 *Watchlist surveillée automatiquement:*\n\n"
    msg += "Actions: " + ", ".join(STOCK_WATCHLIST) + "\n"
    msg += "Crypto: " + ", ".join(CRYPTO_WATCHLIST)
    await update.message.reply_markdown(msg, reply_markup=MENU)


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gère les appuis sur les boutons du menu (ReplyKeyboardMarkup)."""
    text = update.message.text
    chat_id = update.effective_chat.id

    if text == "📈 Nouveau signal":
        await update.message.reply_text("Choisis une paire :", reply_markup=PAIRS_MENU)
        return

    if text == "📋 Watchlist":
        await watchlist(update, context)
        return

    if text == "⬅️ Retour":
        user_state.pop(chat_id, None)
        await update.message.reply_text("Menu principal", reply_markup=MENU)
        return

    if text in CRYPTO_PAIRS or text in STOCK_PAIRS:
        user_state[chat_id] = {"pair": text}
        await update.message.reply_text(
            f"Paire choisie: {text}\nChoisis une durée d'analyse :",
            reply_markup=DURATION_MENU,
        )
        return

    if text in DURATION_MAP:
        pair = user_state.get(chat_id, {}).get("pair")
        if not pair:
            await update.message.reply_text(
                "Choisis d'abord une paire via '📈 Nouveau signal'.", reply_markup=MENU
            )
            return

        await update.message.reply_text(f"Analyse de {pair} ({text}) en cours...")
        cfg = DURATION_MAP[text]
        try:
            if pair in CRYPTO_PAIRS:
                df = get_crypto_data(pair, timeframe=cfg["crypto_tf"])
            else:
                df = get_stock_data(pair, period=cfg["stock_period"], interval=cfg["stock_interval"])

            if df.empty:
                await update.message.reply_text(f"Aucune donnée trouvée pour {pair}.", reply_markup=MENU)
                return

            result = analyze(df)
            await update.message.reply_markdown(
                format_analysis(f"{pair} ({text})", result), reply_markup=MENU
            )
        except Exception as e:
            logger.exception("Erreur menu_handler")
            await update.message.reply_text(f"Erreur lors de l'analyse: {e}", reply_markup=MENU)
        return

    # Texte non reconnu -> on rappelle le menu principal
    await update.message.reply_text("Choisis une option :", reply_markup=MENU)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit une photo de graphique envoyée par l'utilisateur et l'analyse via Gemini Vision."""
    await update.message.reply_text("📷 Analyse du graphique en cours...")
    try:
        photo = update.message.photo[-1]  # plus haute résolution disponible
        photo_file = await photo.get_file()
        image_bytes = await photo_file.download_as_bytearray()

        analysis_text = analyze_chart_image(bytes(image_bytes))

        reply = (
            f"{analysis_text}\n\n"
            "_⚠️ Lecture visuelle automatisée par IA, pas un conseil financier. "
            "Vérifie toujours par toi-même avant de trader._"
        )
        await update.message.reply_markdown(reply)
    except Exception as e:
        logger.exception("Erreur handle_photo")
        await update.message.reply_text(f"Erreur lors de l'analyse de l'image: {e}")


# ---------------------------------------------------------------------------
# SURVEILLANCE AUTOMATIQUE EN ARRIÈRE-PLAN
# ---------------------------------------------------------------------------

async def background_monitor(app: Application):
    """Boucle qui tourne en continu et envoie une alerte si un signal apparaît."""
    while True:
        try:
            for ticker in STOCK_WATCHLIST:
                df = get_stock_data(ticker)
                if df.empty:
                    continue
                result = analyze(df)
                if result["signals"]:
                    text = format_analysis(ticker, result)
                    await app.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")

            for symbol in CRYPTO_WATCHLIST:
                df = get_crypto_data(symbol)
                if df.empty:
                    continue
                result = analyze(df)
                if result["signals"]:
                    text = format_analysis(symbol, result)
                    await app.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="Markdown")

        except Exception as e:
            logger.exception("Erreur dans background_monitor")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def post_init(app: Application):
    # Lance la surveillance en tâche de fond une fois le bot démarré
    asyncio.create_task(background_monitor(app))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if TELEGRAM_TOKEN == "PASTE_YOUR_TOKEN_HERE":
        raise RuntimeError(
            "Configure la variable d'environnement TELEGRAM_TOKEN avant de lancer le bot."
        )

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("signal", signal_stock))
    app.add_handler(CommandHandler("cryptosignal", signal_crypto))
    app.add_handler(CommandHandler("watchlist", watchlist))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    logger.info("Bot démarré.")
    app.run_polling()


if __name__ == "__main__":
    main()
