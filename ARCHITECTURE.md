# 🏗️ ARCHITECTURE TECHNIQUE - CHARTIST-BOT

Documentation complète de l'architecture, des composants, et de l'intégration.

---

## 📐 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                    CHARTIST-BOT ENGINE                      │
│                   (bot_engine.py)                           │
└───────────┬────────────────────────────┬──────────────────┘
            │                            │
    ┌───────▼────────┐          ┌────────▼─────────┐
    │  DATA LAYER    │          │  EXECUTION LAYER │
    ├────────────────┤          ├──────────────────┤
    │ data_fetcher   │          │  trade_executor  │
    │ └─ Deriv API   │          │  risk_manager    │
    │ └─ WebSocket   │          │  position_mgr    │
    └────────┬────────┘          └────────┬─────────┘
             │                           │
    ┌────────▼────────┐          ┌────────▼─────────┐
    │  ANALYSIS LAYER │          │  ALERTS LAYER    │
    ├────────────────┤          ├──────────────────┤
    │ pattern_detector│          │  alerts_handler  │
    │ confirmation_sys│          │  └─ Telegram     │
    │ atr_calculator │          │  └─ Webhooks     │
    └────────────────┘          └──────────────────┘
```

---

## 🔧 Composants Principaux

### 1. **data_fetcher.py** - Connexion aux Données
**Responsabilité:** Récupérer les candlesticks en temps réel de Deriv

```
DerivDataFetcher
├── __init__(app_id, api_token, api_endpoint)
├── connect()
│   └─ Établit WebSocket avec Deriv
├── subscribe_candles(pair, timeframe)
│   └─ S'abonne aux mises à jour
├── _on_message(data)
│   ├─ Traite authentification
│   ├─ Traite candlesticks
│   └─ Déclenche callbacks
├── get_candles(pair, timeframe) → List[Candlestick]
└── get_last_candle(pair, timeframe) → Candlestick
```

**Exemple d'utilisation:**
```python
fetcher = DerivDataFetcher("APP_ID", "TOKEN")
fetcher.connect()
fetcher.subscribe_candles("BOOM1000", "5m")
candles = fetcher.get_candles("BOOM1000", "5m")
```

---

### 2. **pattern_detector.py** - Détection de Figures
**Responsabilité:** Reconnaître les patterns chartistes

```
PatternDetector
├── detect(candles, pair, timeframe) → List[PatternSignal]
│   ├─ _detect_head_shoulders()
│   ├─ _detect_double_top_bottom()
│   └─ _detect_triangles()
├── _find_local_maximum(prices, start, end)
├── _find_local_minimum(prices, start, end)
├── _classify_triangle(highs, lows)
└─ Helper functions
```

**Processus de détection:**
```
1. Récupérer les 50 dernières candlesticks
2. Pour chaque pattern type:
   a. Identifier extremums locaux
   b. Valider structure (pics/creux alignés)
   c. Vérifier proportions (tolerance)
   d. Créer PatternSignal si valide
3. Retourner liste de signaux détectés
```

**Structure PatternSignal:**
```python
PatternSignal(
    pattern_type: PatternType,           # HEAD_SHOULDERS, DOUBLE_TOP, etc.
    direction: TradeDirection,           # LONG ou SHORT
    entry_level: float,                  # Prix d'entrée suggéré
    stop_loss: float,
    take_profit: float,
    resistance_level: float,
    support_level: float,
    confidence_score: float              # 0-1
)
```

---

### 3. **confirmation_system.py** - Validation des Signaux
**Responsabilité:** Confirmer un signal avant d'ouvrir un trade

```
ConfirmationSystem
├── confirm_signal(signal, candles_tf1, candles_tf2)
│   ├─ PullbackDetector.detect_pullback()
│   ├─ ATRCalculator.calculate_atr()
│   ├─ MultiTimeframeConfirmation.is_confirmed()
│   └─ Score final
└─ Retourne (confirmed: bool, details: dict)

ATRCalculator
├── calculate_atr(candles, period=14) → float
└── get_volatility_level(atr, price) → "low|medium|high"

PullbackDetector
├── detect_pullback(candles, signal) → (bool, float)
└── get_fibonacci_levels(high, low) → dict

MultiTimeframeConfirmation
├── determine_trend(candles) → "up|down|sideways"
└── is_confirmed(signal_dir, trend_dir) → bool
```

**Critères de confirmation:**
```
1. Pullback (38.2% Fibonacci) ✓
   └─ Après pattern, prix doit retracer vers SL
   
2. ATR (volatilité) ✓
   └─ ATR doit être cohérent avec pattern size
   
3. Multi-Timeframe ✓
   └─ M5 signal confirmé par M15 trend
   
Score final = Signal confidence + (3 × 0.1 si tout OK)
Seuil activation = confiance > 65%
```

---

### 4. **risk_manager.py** - Gestion du Risque
**Responsabilité:** Calculs de position sizing et limites de risque

```
RiskManager
├── calculate_position_size(signal, atr)
│   └─ Retourne: (position_size, risk_amount, entry)
├── set_tp_sl(signal, atr, min_ratio=1.5)
│   └─ Retourne: (entry, stop_loss, take_profit)
├── can_open_trade() → bool
│   ├─ Vérifier max positions concurrentes
│   └─ Vérifier daily loss limit
└── record_trade_loss(loss)

KellyCriterion
└── calculate_kelly_fraction(win_rate, avg_win, avg_loss) → float

PositionManager
├── add_position(trade_id, position_data)
├── close_position(trade_id, exit_price, reason)
└── get_open_positions() → dict

DrawdownTracker
├── update(current_balance)
└── get_current_drawdown() → (drawdown, drawdown_pct)
```

**Formule Position Sizing:**
```
Risk Amount = Account Balance × Risk Percent (1.5%)
Stop Loss Distance = Entry - SL (ajusté par ATR)
Position Size = Risk Amount / Stop Loss Distance
Max Position Value = Account Balance × 5%
```

**Exemple:**
```
Account: 10,000 USD
Risk Percent: 1.5%
Risk Amount = 10,000 × 1.5% = 150 USD

Signal: Entry 1245.30, SL 1240.30
Distance = 1245.30 - 1240.30 = 5.00
Position Size = 150 / 5 = 30 contrats
```

---

### 5. **bot_engine.py** - Orchestrateur Principal
**Responsabilité:** Coordination de tous les composants

```
ChartistBotEngine
├── initialize()
│   ├─ Créer DataFetcher
│   ├─ Créer PatternDetector
│   ├─ Créer ConfirmationSystem
│   ├─ Créer RiskManager
│   └─ S'abonner aux paires
│
├── start()
│   └─ Boucle principale (event-driven)
│
├── _on_new_candle(pair, timeframe)
│   ├─ Récupérer candlesticks
│   ├─ Détecter patterns
│   └─ Pour chaque pattern:
│       ├─ Confirmer signal
│       ├─ Vérifier conditions trading
│       └─ Exécuter si OK
│
├── _execute_trade(setup, pair, timeframe)
│   ├─ Créer ActiveTrade
│   ├─ Enregistrer position
│   └─ Déclencher callbacks
│
├── update_trade(trade_id, current_price)
│   └─ Mettre à jour PnL et vérifier exits
│
├── _close_trade(trade_id, exit_price, reason)
│   ├─ Calculer PnL final
│   ├─ Enregistrer trade fermé
│   └─ Déclencher callbacks
│
└── Callbacks Management
    ├── add_callback(callback, event_type)
    ├── _trigger_signal_callbacks(signal, details)
    ├── _trigger_trade_callbacks(trade, event)
    └── _trigger_alert_callbacks(alert)
```

**Workflow d'une trade:**
```
1. Nouvelle candlestick reçue
   ↓
2. Pattern détecté? Non → Continue
   Oui ↓
3. Signal confirmé? Non → Alert (optionnel)
   Oui ↓
4. Can open trade? (max positions, max loss) Non → Skip
   Oui ↓
5. Calculer Entry/SL/TP et Position Size
   ↓
6. EXÉCUTER TRADE
   ├─ Ouvrir position
   ├─ Enregistrer trade
   ├─ Alert Telegram ✓
   ↓
7. Monitor Position
   ├─ Mettre à jour PnL à chaque tick
   ├─ Vérifier SL atteint? → Close
   ├─ Vérifier TP atteint? → Close
   ↓
8. FERMER TRADE
   ├─ Calculer PnL final
   ├─ Enregistrer fermeture
   ├─ Alert Telegram ✓
   └─ Mettre à jour statistiques
```

---

### 6. **alerts_handler.py** - Notifications
**Responsabilité:** Envoyer les alertes via Telegram

```
TelegramAlertsHandler
├── __init__(bot_token, chat_id)
├── send_message(message, parse_mode="HTML")
├── handle_signal(signal, details)
├── handle_trade(trade, event)
├── handle_alert(alert)
└── _format_*_message() → str

WebhookAlertsHandler
└── send_event(event_type, data) → bool
```

**Types d'alertes:**
```
1. Signal Pattern Détecté
   └─ Toutes les infos du pattern
   
2. Trade Ouvert
   └─ Entry, SL, TP, Direction, Size
   
3. Trade Fermé
   └─ PnL, Raison, Temps total
   
4. Alerte Système
   └─ Warnings, Errors (si seuil atteint)
```

---

## 🔄 Flux de Données

```
Deriv API (WebSocket)
    ↓
DataFetcher.receive_candle()
    ↓
Store in candlesticks[pair][timeframe]
    ↓
Trigger callback: _on_new_candle()
    ↓
PatternDetector.detect()
    ├─ H&S Detection
    ├─ Double Top/Bottom Detection
    └─ Triangle Detection
    ↓
For each pattern → PatternSignal
    ↓
ConfirmationSystem.confirm_signal()
    ├─ Pullback check
    ├─ ATR check
    └─ Multi-TF check
    ↓
If Confirmed:
    ├─ RiskManager.calculate_position_size()
    ├─ RiskManager.set_tp_sl()
    └─ BotEngine._execute_trade()
        ├─ Create ActiveTrade
        ├─ PositionManager.add_position()
        └─ Trigger callbacks
            ├─ TelegramAlertsHandler.handle_trade()
            └─ Logger
```

---

## 📊 Structure des Données

### Candlestick
```python
@dataclass
class Candlestick:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
    # Properties
    .body       # Close - Open
    .range      # High - Low
    .is_bullish # Close > Open
    .is_bearish # Close < Open
```

### ActiveTrade
```python
@dataclass
class ActiveTrade:
    id: str                      # Unique ID
    pair: str
    timeframe: str
    direction: TradeDirection    # LONG ou SHORT
    
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    
    entry_time: datetime
    current_price: float         # Dernière mise à jour
    
    pnl: float                   # Profit/Loss courant
    pnl_percent: float
    
    status: TradeStatus          # OPEN, CLOSED, etc.
    exit_time: Optional[datetime]
    exit_reason: Optional[str]   # TP, SL, Manual
```

---

## ⚙️ Configuration (config.json)

```json
{
  "trading": {
    "pairs": ["BOOM1000", ...],
    "timeframes": ["5m", "15m"],
    "risk_per_trade_percent": 1.5,
    "max_daily_trades": 20,
    "max_concurrent_positions": 3,
    "max_daily_loss_percent": 5.0
  },
  "pattern_detection": {
    "sensitivity": "medium",
    "lookback_bars": 50
  },
  "confirmation": {
    "multi_timeframe": true,
    "pullback_required": true,
    "pullback_percent": 38.2,
    "atr_multiplier": 1.5
  }
}
```

---

## 🧪 Extension et Customization

### Ajouter un nouveau Pattern

1. **Créer la fonction dans pattern_detector.py:**
```python
def _detect_wedge(self, candles, pair, timeframe):
    # Logic pour détecter wedges
    signals = []
    # ...
    return signals
```

2. **Appeler dans detect():**
```python
def detect(self, candles, pair, timeframe):
    signals = []
    signals.extend(self._detect_wedge(candles, pair, timeframe))
    return signals
```

3. **Ajouter le type PatternType:**
```python
class PatternType(Enum):
    WEDGE = "wedge"
```

### Ajouter un nouvel Indicateur

1. **Créer dans AnalysisUtils:**
```python
@staticmethod
def calculate_stochastic(prices, period=14):
    # Logique
    return stoch_values
```

2. **Utiliser dans confirmation_system.py:**
```python
stoch = AnalysisUtils.calculate_stochastic(closes)
# Utiliser pour confirmation
```

### Intégrer un nouveau Broker

1. **Créer data_fetcher_weltrade.py** (copie de data_fetcher.py)
2. **Adapter API calls à Weltrade**
3. **Modifier bot_engine.py pour supporter 2 fetchers:**
```python
self.fetchers = {
    'deriv': DerivDataFetcher(...),
    'weltrade': WeltradeFetcher(...)
}
```

---

## 📈 Performance et Optimisation

### Complexité Temporelle

| Opération | Complexité | Temps |
|-----------|-----------|-------|
| Pattern Detection | O(n) où n=lookback | ~100ms |
| ATR Calculation | O(period) | ~5ms |
| Multi-TF Check | O(1) | ~1ms |
| Position Sizing | O(1) | <1ms |
| **Total par candlestick** | | **~110ms** |

### Optimisations Implémentées

1. **Caching**: Les candlesticks sont bufferisées (pas de recalcul)
2. **Lock-free reads**: Data updates sont atomic
3. **Async callbacks**: Notifications n'bloquent pas le trading
4. **Lazy evaluation**: Patterns vérifiés uniquement sur nouvelles candles

---

## 🔒 Sécurité

### Credentials
- ✅ Stockés dans .env (jamais en hard-code)
- ✅ Loaded via python-dotenv
- ✅ API token minimal (Trade + Admin seulement)

### Risk Limits
- ✅ Max 1.5% risque par trade
- ✅ Max 5% drawdown journalier
- ✅ Max 3 positions concurrentes
- ✅ Max 20 trades/jour

### Validation
- ✅ All prices > 0 et finite
- ✅ High >= Low, Open/Close in [Low, High]
- ✅ Position size in [0, 1000000]
- ✅ Risk percent in (0, 5]

---

## 🚀 Next Steps pour Amélioration

**Phase 2 (Backtesting):**
- Implémenter backtest_engine.py
- Ajouter optimizer.py avec grid search
- Générer performance reports

**Phase 3 (Dashboard):**
- Web UI avec Dash/Flask
- Real-time charts
- Trade history
- Performance analytics

**Phase 4 (ML):**
- Pattern recognition par ML
- Probability scoring
- Adaptive parameters

---

**Questions? Me contacter anytime! 🚀**
