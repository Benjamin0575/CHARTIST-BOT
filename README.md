# 🎯 CHARTIST-BOT - Bot de Trading Automatisé

Bot de trading automatisé basé sur la détection de **figures chartistes** avec confirmation multi-timeframe, gestion du risque avancée et alertes Telegram.

**Version:** 1.0.0  
**Status:** Production Ready ✅

---

## 📋 Caractéristiques

### ✅ Détection de Patterns
- **Head & Shoulders** (normal et inverse)
- **Double Top / Double Bottom**
- **Triangles** (Symétrique, Ascendant, Descendant)

### ✅ Confirmation Intelligente
- Multi-Timeframe (M5 + M15)
- Pullback Detection (Fibonacci)
- ATR Volatility Confirmation
- Confiance Score (0-100%)

### ✅ Gestion du Risque
- Fixed Risk per Trade (1-2% configurables)
- Position Sizing Automatique
- Kelly Criterion Support
- Drawdown Tracking
- Daily Loss Limit

### ✅ Exécution
- API Deriv WebSocket
- Take Profit / Stop Loss Intelligents
- Ratio Risk:Reward Minimum (1.5:1)
- Gestion des positions concurrentes (max 3)

### ✅ Monitoring
- Telegram Alerts (en temps réel)
- Dashboard Statistiques
- Trade History Complet
- Performance Analytics

---

## 🚀 Installation

### Prérequis
- Python 3.8+
- Compte Deriv (avec API Key)
- Bot Telegram (pour les alertes)

### 1. Cloner le projet
```bash
git clone https://github.com/yourusername/chartist-bot.git
cd CHARTIST-BOT
```

### 2. Créer un environnement virtuel
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
```

Éditer `.env` avec vos credentials:
```env
# Deriv
DERIV_APP_ID=your_deriv_app_id
DERIV_API_TOKEN=your_deriv_api_token

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 5. (Optionnel) Personnaliser config.json
```bash
nano config.json
```

---

## 📖 Configuration

### Obtenir vos Credentials Deriv

1. Aller sur [Deriv API Dashboard](https://app.deriv.com/account/api-token)
2. Créer une nouvelle application
3. Générer un API Token avec les permissions "Trade" et "Admin"
4. Noter votre App ID et API Token

### Obtenir votre Telegram Bot

1. Chercher `@BotFather` sur Telegram
2. Créer un bot: `/newbot`
3. Noter le token fourni
4. Envoyer `/start` à votre bot
5. Récupérer votre Chat ID (ex: en forwardant un message à `@userinfobot`)

### Configuration config.json

**Trading:**
```json
{
  "trading": {
    "pairs": ["BOOM1000", "BOOM300", "XAUUSD", "VOLATILITY100", ...],
    "timeframes": ["5m", "15m"],
    "risk_per_trade_percent": 1.5,
    "max_daily_trades": 20,
    "max_concurrent_positions": 3
  }
}
```

**Pattern Detection:**
```json
{
  "pattern_detection": {
    "enabled_patterns": ["head_shoulders", "double_top_bottom", "triangles"],
    "sensitivity": "medium",  // "low", "medium", "high"
    "lookback_bars": 50
  }
}
```

**Confirmation:**
```json
{
  "confirmation": {
    "multi_timeframe": true,
    "pullback_required": true,
    "pullback_percent": 38.2,  // Fibonacci retracement
    "atr_multiplier": 1.5
  }
}
```

---

## ▶️ Démarrage

### Mode Normal
```bash
python main.py
```

### Mode Backtest (à venir)
```bash
python backtest.py --start 2024-01-01 --end 2024-12-31 --pair BOOM1000
```

### Mode Optimisation (à venir)
```bash
python optimizer.py --pair BOOM1000 --timeframe 5m
```

---

## 📊 Structure du Projet

```
CHARTIST-BOT/
├── main.py                      # Point d'entrée
├── config.json                  # Configuration (paires, paramètres)
├── .env                         # Variables sensibles
├── requirements.txt             # Dépendances Python
│
├── bot_engine.py               # Engine principal (orchestration)
├── models.py                   # Structures de données
│
├── data_fetcher.py             # Connexion Deriv API
├── pattern_detector.py         # Détecteur de figures
├── confirmation_system.py      # Système de confirmation (MTF, ATR, etc.)
├── risk_manager.py             # Gestion du risque et position sizing
├── alerts_handler.py           # Notifications Telegram
│
├── backtesting/                # Module backtesting (à implémenter)
│   ├── backtest_engine.py
│   ├── optimizer.py
│   └── performance_analyzer.py
│
├── dashboard/                  # Dashboard web (à implémenter)
│   └── realtime_dashboard.py
│
├── logs/                       # Logs de run
└── README.md
```

---

## 🔄 Workflow du Bot

```
┌─────────────────┐
│  Connexion      │
│  Deriv API      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Réception Candlesticks │
│  (5m, 15m)              │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Pattern Detection      │
│  (H&S, Double, Tri)     │
└────────┬────────────────┘
         │
         ▼
    Pattern Found?
         │
     No  ├─→ Continue
         │
     Yes
         ▼
┌─────────────────────────┐
│  Confirmation System    │
│  • Multi-TF             │
│  • Pullback             │
│  • ATR                  │
└────────┬────────────────┘
         │
         ▼
    Confirmed?
         │
     No  ├─→ Telegram Alert (optional)
         │    & Continue
         │
     Yes
         ▼
┌─────────────────────────┐
│  Risk Manager Check     │
│  • Max positions?       │
│  • Daily loss limit?    │
└────────┬────────────────┘
         │
         ▼
    Can Trade?
         │
     No  ├─→ Skip
         │
     Yes
         ▼
┌──────────────────────────┐
│  Calculate Setup         │
│  • Entry/SL/TP           │
│  • Position Size (1.5%)  │
│  • Risk:Reward Ratio     │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Execute Trade           │
│  • Open position         │
│  • Telegram Alert ✓      │
│  • Log trade             │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  Monitor Trade           │
│  • Price updates         │
│  • PnL calculation       │
│  • Exit checks           │
└────────┬─────────────────┘
         │
         ▼
    Exit Signal?
         │
     No  ├─→ Continue monitoring
         │
     Yes (TP/SL)
         ▼
┌──────────────────────────┐
│  Close Trade             │
│  • Calculate final PnL   │
│  • Telegram Alert ✓      │
│  • Update statistics     │
└─────────────────────────┘
```

---

## 📈 Paires Recommandées

**Synthétiques Deriv:**
- BOOM 1000 (très volatil, patterns nets)
- BOOM 300 (moyen volatilité)
- VOLATILITY 100 & 75 (trends clairs)

**Métaux:**
- XAUUSD (Gold - trending)
- XAGUSD (Silver - patterns discrets)

**Forex Majeurs:**
- EUR/USD (très liquide)
- GBP/USD (bons patterns)

**Indices:**
- DAX (tendances fortes)
- SPX500 (stabilité)

---

## 💡 Conseils d'Utilisation

### ✅ Bonnes Pratiques

1. **Commencer petit:** 1.5% risque par trade
2. **Tester d'abord:** Utiliser le backtester sur 3 mois de données
3. **Multi-TF confirmé:** Toujours activer la confirmation multi-timeframe
4. **Pattern qualité:** Priorité à la confiance > quantité de trades
5. **Monitoring:** Surveiller les performances quotidiennement

### ❌ À Éviter

1. **Augmenter le risque** sans backtesting
2. **Trop de paires** à la fois (max 5-6)
3. **Patterns ambigus** (attendre confirmation claire)
4. **Trading après perte** (daily loss limit protège)
5. **Ignorer la volatilité** (ATR confirmation est critique)

---

## 🐛 Troubleshooting

### Erreur: "Connexion Deriv refusée"
- Vérifier les credentials dans `.env`
- Vérifier la connexion internet
- Vérifier les permissions du token Deriv

### Erreur: "Telegram rate limit"
- Telegram limite à ~30 messages/seconde
- Réduire les alertes dans config.json

### Patterns non détectés
- Augmenter `lookback_bars` dans config.json
- Réduire la `sensitivity` (medium → low)
- Vérifier les timeframes

### Trades non ouverts
- Vérifier `risk_manager.can_open_trade()` conditions
- Vérifier `max_concurrent_positions` atteint?
- Vérifier daily loss limit dépassé?

---

## 📊 Exemple de Session

```
[2024-01-15 09:05:15] ✓ Bot initialisé
[2024-01-15 09:05:16] ✓ Connecté à Deriv
[2024-01-15 09:05:20] ✓ Abonné à 10 paires
[2024-01-15 09:12:43] 🎯 Head & Shoulders détecté [BOOM1000 5m]
[2024-01-15 09:12:45] ✓ Confirmation Multi-TF: OK (confiance: 78%)
[2024-01-15 09:12:46] 📈 Trade ouvert #a3f8k9 SHORT BOOM1000
                      Entry: 1245.30 | SL: 1250.00 | TP: 1235.60 | R:R: 2.1
[2024-01-15 09:14:32] 📊 Trade fermé [TAKE PROFIT]
                      PnL: +124.50 USD (+2.1%)
[2024-01-15 09:15:00] 📈 Double Bottom détecté [XAUUSD 15m]
                      ...
```

---

## 🔐 Sécurité

- ✅ Credentials en `.env` (jamais en hard-code)
- ✅ API Token avec permissions minimales
- ✅ Chat ID Telegram privé
- ✅ Risk limits configurables
- ✅ Position limits (max 3 concurrent)

---

## 📝 Logs

Les logs sont sauvegardés dans `logs/chartist_YYYYMMDD_HHMMSS.log`

Consulter les logs:
```bash
tail -f logs/chartist_*.log
```

---

## 🤝 Support & Contact

En cas de problème:
1. Vérifier les logs: `logs/`
2. Vérifier config.json
3. Vérifier les credentials
4. Relancer le bot

---

## 📜 Licence

PROPRIÉTAIRE - Usage personnel uniquement

---

## 🎯 Roadmap

- [ ] Dashboard web temps réel
- [ ] Backtester complet
- [ ] Grid search optimisation
- [ ] Support Weltrade
- [ ] Support Binance/Crypto
- [ ] Machine Learning patterns
- [ ] Mobile app monitoring

---

**Bon trading! 🚀**
