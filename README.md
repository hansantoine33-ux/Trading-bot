# Bot Telegram d'analyse technique (RSI + MACD + Bollinger)

## Ce que fait ce bot

- Surveille en continu une liste d'actions (Yahoo Finance) et de cryptos (Binance)
- Calcule RSI, MACD et Bollinger Bands toutes les 30 minutes
- T'envoie un message Telegram automatique quand un signal apparaît
  (survente/surachat, croisement MACD, prix qui touche les bandes de Bollinger)
- Répond aussi à des commandes à la demande :
  - `/signal AAPL` → analyse une action
  - `/cryptosignal BTC/USDT` → analyse une crypto
  - `/watchlist` → affiche la liste surveillée

⚠️ **Ce n'est pas un conseil financier.** Les signaux techniques sont des
indicateurs statistiques, pas des garanties. Ne base pas de décisions
d'investissement uniquement sur ce bot.

## Étape 1 — Récupérer ton token et ton chat ID

1. Sur Telegram, parle à **@BotFather** → `/newbot` → suis les étapes
2. Note le **token** qu'il te donne
3. Démarre une conversation avec ton nouveau bot (clique Start)
4. Va sur `https://api.telegram.org/bot<TON_TOKEN>/getUpdates` dans ton navigateur
   après avoir envoyé un message au bot, pour récupérer ton **chat_id**

## Étape 2 — Tester en local (optionnel)

```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN="ton_token_ici"
export CHAT_ID="ton_chat_id_ici"
python bot.py
```

Le bot tourne tant que ton terminal reste ouvert. Utile pour tester avant de déployer.

## Étape 3 — Déployer sur Railway (gratuit pour démarrer, tourne 24/7)

1. Crée un compte sur [railway.app](https://railway.app) (connexion via GitHub)
2. Mets ce dossier dans un repo GitHub (ou utilise "Deploy from local directory" si proposé)
3. Sur Railway : **New Project → Deploy from GitHub repo**
4. Dans l'onglet **Variables**, ajoute :
   - `TELEGRAM_TOKEN` = ton token
   - `CHAT_ID` = ton chat id
5. Railway détecte le `Procfile` et lance automatiquement `python bot.py`
6. Le bot tourne en continu — tu reçois les alertes même PC éteint

## Personnalisation

Dans `bot.py`, modifie directement :

```python
STOCK_WATCHLIST = ["AAPL", "TSLA", "MSFT"]
CRYPTO_WATCHLIST = ["BTC/USDT", "ETH/USDT"]
CHECK_INTERVAL_SECONDS = 60 * 30  # fréquence de vérification
```

Tu peux aussi ajuster les seuils RSI (30/70) ou les périodes des indicateurs
dans les fonctions `compute_rsi`, `compute_macd`, `compute_bollinger`.
