# 🤖 Bot Telegram Trading PRO (Signaux techniques)

Ce bot Telegram analyse les marchés Forex (via données réelles Yahoo Finance) et génère des signaux de trading basés sur des indicateurs techniques :

- RSI
- MACD
- Bandes de Bollinger
- Tendance EMA (50 / 200)

> ⚠️ **Important :** Ce bot ne fait aucun trading automatique. Il fournit uniquement des analyses et signaux informatifs.

---

## 📊 Fonctionnalités

- 📈 Génération de signaux **BUY / SELL / NO TRADE**
- 💱 Support des paires Forex OTC (converties en symboles Yahoo Finance)
- ⏱ Choix de durée : 1 min, 3 min, 5 min
- 📉 Analyse multi-indicateurs :
  - RSI (surachat / survente)
  - MACD (momentum)
  - Bandes de Bollinger (excès de prix)
  - EMA 50/200 (tendance)
- 🤖 Interface Telegram avec menus interactifs

---

## 🧠 Logique des signaux

Le bot calcule un **score global** basé sur les indicateurs :

| Indicateur | Rôle |
|---|---|
| EMA 50/200 | Direction principale (tendance) |
| RSI | Détection des zones extrêmes |
| MACD | Confirmation du momentum |
| Bollinger | Détection des excès de prix |

Chaque indicateur contribue avec **+1** (signal haussier) ou **−1** (signal baissier).

### Décision finale

| Score | Signal |
|---|---|
| ≥ 3 + tendance haussière | 🟢 **STRONG BUY** |
| ≤ −3 + tendance baissière | 🔴 **STRONG SELL** |
| Conditions non fiables | ⚪ **NO TRADE** |

---

## 📦 Installation

### 1. Prérequis

- Python **3.9** ou supérieur
- Un compte Telegram et un **Bot Token** (via [@BotFather](https://t.me/BotFather))

### 2. Cloner le projet

```bash
git clone https://github.com/votre-utilisateur/telegram-trading-bot.git
cd telegram-trading-bot
```

### 3. Installer les dépendances

```bash
pip install python-telegram-bot pandas numpy yfinance
```

### 4. Configurer le bot

Créez un fichier `.env` ou modifiez directement `config.py` :

```env
TELEGRAM_TOKEN=your_telegram_bot_token_here
```

### 5. Lancer le bot

```bash
python bot.py
```

---

## 🗂️ Structure du projet

```
telegram-trading-bot/
├── bot.py              # Point d'entrée principal
├── config.py           # Configuration (token, paramètres)
├── signals.py          # Logique d'analyse technique
├── indicators.py       # Calcul RSI, MACD, Bollinger, EMA
├── requirements.txt    # Dépendances Python
└── README.md
```

---

## 📡 Paires Forex supportées

Le bot supporte les principales paires OTC, converties automatiquement en symboles Yahoo Finance :

| Paire OTC | Symbole Yahoo Finance |
|---|---|
| EUR/USD OTC | `EURUSD=X` |
| GBP/USD OTC | `GBPUSD=X` |
| USD/JPY OTC | `USDJPY=X` |
| AUD/USD OTC | `AUDUSD=X` |
| USD/CAD OTC | `USDCAD=X` |

---

## ⚙️ Dépendances

| Package | Version recommandée | Usage |
|---|---|---|
| `python-telegram-bot` | ≥ 20.0 | Interface Telegram |
| `pandas` | ≥ 1.5 | Manipulation des données |
| `numpy` | ≥ 1.23 | Calculs numériques |
| `yfinance` | ≥ 0.2 | Données marché Yahoo Finance |

---

## ⚠️ Avertissement

> Ce bot est un outil d'**aide à la décision** uniquement. Les signaux générés sont basés sur une analyse technique automatisée et **ne constituent pas des conseils financiers**. Le trading Forex implique un risque de perte en capital. Utilisez cet outil à vos propres risques.

---

## 📄 Licence

Ce projet est distribué sous licence **MIT**. Voir le fichier `LICENSE` pour plus de détails.
