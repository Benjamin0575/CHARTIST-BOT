"""
Engine principal du bot CHARTIST
Orchestre: Data fetching, Pattern detection, Confirmation, Trading
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable
from collections import defaultdict

from data_fetcher import DerivDataFetcher
from pattern_detector import PatternDetector
from confirmation_system import ConfirmationSystem, ATRCalculator
from risk_manager import RiskManager, PositionManager, DrawdownTracker
from models import (
    PatternSignal, ActiveTrade, TradingStatistics, Alert, TradeStatus, TradeDirection
)


logger = logging.getLogger(__name__)


class ChartistBotEngine:
    """Engine principal du bot CHARTIST"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration du bot (de config.json)
        """
        self.config = config
        self.is_running = False
        
        # Composants principaux
        self.data_fetcher: Optional[DerivDataFetcher] = None
        self.pattern_detector: Optional[PatternDetector] = None
        self.confirmation_system: Optional[ConfirmationSystem] = None
        self.risk_manager: Optional[RiskManager] = None
        self.position_manager = PositionManager()
        self.drawdown_tracker = DrawdownTracker()
        
        # Données et état
        self.active_trades: Dict[str, ActiveTrade] = {}
        self.closed_trades: List[ActiveTrade] = []
        self.pending_signals: List[PatternSignal] = []
        self.alerts: List[Alert] = []
        self.statistics = TradingStatistics()
        
        # Callbacks
        self.on_signal_callbacks: List[Callable] = []
        self.on_trade_callbacks: List[Callable] = []
        self.on_alert_callbacks: List[Callable] = []
        
        # Métriques
        self.start_time = datetime.now()
        self.last_detection_time = {}
    
    def initialize(self) -> bool:
        """Initialise tous les composants"""
        try:
            logger.info("Initialisation du bot CHARTIST...")
            
            # Data fetcher
            deriv_config = self.config['deriv']
            self.data_fetcher = DerivDataFetcher(
                app_id=deriv_config['app_id'],
                api_token=deriv_config['api_token'],
                api_endpoint=deriv_config['api_endpoint']
            )
            
            # Connecter et s'abonner
            if not self.data_fetcher.connect():
                logger.error("Impossible de se connecter à Deriv")
                return False
            
            # Pattern detector
            pattern_config = self.config['pattern_detection']
            self.pattern_detector = PatternDetector(
                sensitivity=pattern_config.get('sensitivity', 'medium'),
                lookback=pattern_config.get('lookback_bars', 50)
            )
            
            # Confirmation system
            self.confirmation_system = ConfirmationSystem(
                self.config['confirmation']
            )
            
            # Risk manager
            trading_config = self.config['trading']
            initial_balance = self.config['backtesting'].get('initial_balance', 10000)
            self.risk_manager = RiskManager(
                account_balance=initial_balance,
                risk_percent=trading_config['risk_per_trade_percent'],
                max_daily_loss_percent=trading_config.get('max_daily_loss_percent', 5.0)
            )
            
            # S'abonner aux pairs
            for pair in trading_config['pairs']:
                for tf in trading_config['timeframes']:
                    self.data_fetcher.subscribe_candles(pair, tf)
            
            # Ajouter les callbacks
            self.data_fetcher.add_callback(self._on_new_candle, "candle")
            self.data_fetcher.add_callback(self._on_connected, "connection")
            
            logger.info("✓ Bot initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation: {e}")
            return False
    
    def start(self):
        """Démarre le bot"""
        if self.is_running:
            logger.warning("Bot déjà en cours d'exécution")
            return
        
        self.is_running = True
        logger.info("🚀 Bot CHARTIST démarré")
        
        # Boucle principale
        try:
            while self.is_running:
                asyncio.sleep(1)
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Arrête le bot"""
        self.is_running = False
        
        if self.data_fetcher:
            self.data_fetcher.close()
        
        logger.info("Bot CHARTIST arrêté")
    
    def _on_connected(self):
        """Callback: Connexion établie"""
        logger.info("✓ Connecté et prêt à trader")
        alert = Alert(
            timestamp=datetime.now(),
            level="INFO",
            message="Bot connecté et abonné aux paires"
        )
        self._add_alert(alert)
    
    def _on_new_candle(self, pair: str, timeframe: str):
        """Callback: Nouvelle candlestick reçue"""
        logger.debug(f"Nouvelle candlestick: {pair} {timeframe}")
        
        # Récupérer les candlesticks
        candles = self.data_fetcher.get_candles(pair, timeframe)
        
        if len(candles) < 15:
            return
        
        # Détecter les patterns
        signals = self.pattern_detector.detect(candles, pair, timeframe)
        
        for signal in signals:
            self._process_signal(signal, candles, pair, timeframe)
    
    def _process_signal(self, signal: PatternSignal, candles_tf1: List,
                       pair: str, timeframe: str):
        """Traite un signal détecté"""
        
        logger.info(f"Pattern détecté: {signal.pattern_type.value} {pair} {timeframe}")
        
        # Vérifier les doublons (anti-spam)
        key = f"{pair}_{timeframe}"
        if key in self.last_detection_time:
            last = self.last_detection_time[key]
            if (datetime.now() - last).total_seconds() < 300:  # < 5 min
                logger.debug("Signal similaire récent ignoré")
                return
        
        self.last_detection_time[key] = datetime.now()
        
        # Confirmation
        if self.config['confirmation'].get('multi_timeframe', False):
            # Récupérer le timeframe supérieur
            tf_mapping = {"5m": "15m", "15m": "1h"}
            upper_tf = tf_mapping.get(timeframe)
            
            if upper_tf:
                candles_tf2 = self.data_fetcher.get_candles(pair, upper_tf)
            else:
                candles_tf2 = None
        else:
            candles_tf2 = None
        
        confirmed, details = self.confirmation_system.confirm_signal(
            signal, candles_tf1, candles_tf2
        )
        
        # Créer l'alerte
        alert = Alert(
            timestamp=datetime.now(),
            level="INFO" if confirmed else "DEBUG",
            message=f"Pattern {signal.pattern_type.value} détecté (confiance: {details['final_confidence']:.0%})",
            pair=pair
        )
        self._add_alert(alert)
        
        # Déclencher les callbacks
        self._trigger_signal_callbacks(signal, details)
        
        if not confirmed:
            return
        
        # Vérifier si on peut ouvrir un trade
        if not self.risk_manager.can_open_trade():
            logger.warning("Conditions de trading non respectées")
            return
        
        # Calculer les TP/SL
        atr = ATRCalculator.calculate_atr(candles_tf1)
        entry, sl, tp = self.risk_manager.set_tp_sl(signal, atr)
        
        # Calculer la position size
        position_size, risk_amount, _ = self.risk_manager.calculate_position_size(signal, atr)
        
        # Créer le setup
        from models import TradeSetup
        setup = TradeSetup(
            signal=signal,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            position_size=position_size,
            risk_amount=risk_amount,
            reward_amount=abs(tp - entry) * position_size,
            risk_reward_ratio=abs(tp - entry) / abs(entry - sl) if sl != entry else 0
        )
        
        # Exécuter le trade
        self._execute_trade(setup, pair, timeframe)
    
    def _execute_trade(self, setup: 'TradeSetup', pair: str, timeframe: str):
        """Exécute un trade"""
        
        trade_id = str(uuid.uuid4())[:8]
        
        trade = ActiveTrade(
            id=trade_id,
            pair=pair,
            timeframe=timeframe,
            direction=setup.signal.direction,
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit=setup.take_profit,
            position_size=setup.position_size,
            entry_time=datetime.now(),
            current_price=setup.entry_price
        )
        
        self.active_trades[trade_id] = trade
        self.position_manager.add_position(trade_id, {
            'entry_price': setup.entry_price,
            'position_size': setup.position_size,
            'direction': setup.signal.direction.value,
            'pair': pair
        })
        
        # Alerte
        alert = Alert(
            timestamp=datetime.now(),
            level="INFO",
            message=f"Trade ouvert: {setup.signal.direction.value.upper()} {pair} @ {setup.entry_price:.5f}",
            pair=pair,
            trade_id=trade_id
        )
        self._add_alert(alert)
        
        logger.info(f"Trade {trade_id} ouvert: {setup.signal.direction.value.upper()} "
                   f"{pair} @ {setup.entry_price:.5f} | SL: {setup.stop_loss:.5f} | "
                   f"TP: {setup.take_profit:.5f} | R:R: {setup.risk_reward_ratio:.2f}")
        
        # Callback
        self._trigger_trade_callbacks(trade, "open")
    
    def update_trade(self, trade_id: str, current_price: float):
        """Met à jour un trade avec le prix actuel"""
        
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        trade.current_price = current_price
        
        # Calculer PnL
        if trade.direction == TradeDirection.LONG:
            trade.pnl = (current_price - trade.entry_price) * trade.position_size
        else:
            trade.pnl = (trade.entry_price - current_price) * trade.position_size
        
        trade.pnl_percent = (trade.pnl / (trade.entry_price * trade.position_size)) * 100
        
        # Vérifier les exits
        if current_price >= trade.take_profit and trade.direction == TradeDirection.LONG:
            self._close_trade(trade_id, trade.take_profit, "Take Profit")
        
        elif current_price <= trade.take_profit and trade.direction == TradeDirection.SHORT:
            self._close_trade(trade_id, trade.take_profit, "Take Profit")
        
        elif current_price <= trade.stop_loss and trade.direction == TradeDirection.LONG:
            self._close_trade(trade_id, trade.stop_loss, "Stop Loss")
        
        elif current_price >= trade.stop_loss and trade.direction == TradeDirection.SHORT:
            self._close_trade(trade_id, trade.stop_loss, "Stop Loss")
    
    def _close_trade(self, trade_id: str, exit_price: float, exit_reason: str):
        """Ferme un trade"""
        
        if trade_id not in self.active_trades:
            return
        
        trade = self.active_trades[trade_id]
        trade.exit_time = datetime.now()
        trade.status = TradeStatus.CLOSED
        trade.exit_reason = exit_reason
        
        # Calculer PnL final
        if trade.direction == TradeDirection.LONG:
            trade.pnl = (exit_price - trade.entry_price) * trade.position_size
        else:
            trade.pnl = (trade.entry_price - exit_price) * trade.position_size
        
        trade.pnl_percent = (trade.pnl / (trade.entry_price * trade.position_size)) * 100
        
        # Enregistrer
        self.closed_trades.append(trade)
        del self.active_trades[trade_id]
        
        # Mise à jour risk manager
        if trade.pnl < 0:
            self.risk_manager.record_trade_loss(abs(trade.pnl))
        
        # Alerte
        alert = Alert(
            timestamp=datetime.now(),
            level="INFO",
            message=f"Trade fermé: {trade.exit_reason} | PnL: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)",
            pair=trade.pair,
            trade_id=trade_id
        )
        self._add_alert(alert)
        
        logger.info(f"Trade {trade_id} fermé: {exit_reason} | PnL: {trade.pnl:.2f} ({trade.pnl_percent:.2f}%)")
        
        # Callback
        self._trigger_trade_callbacks(trade, "close")
    
    def _add_alert(self, alert: Alert):
        """Ajoute une alerte"""
        self.alerts.append(alert)
        self._trigger_alert_callbacks(alert)
    
    def add_callback(self, callback: Callable, event_type: str):
        """Ajoute un callback"""
        if event_type == "signal":
            self.on_signal_callbacks.append(callback)
        elif event_type == "trade":
            self.on_trade_callbacks.append(callback)
        elif event_type == "alert":
            self.on_alert_callbacks.append(callback)
    
    def _trigger_signal_callbacks(self, signal: PatternSignal, details: dict):
        """Déclenche les callbacks de signal"""
        for callback in self.on_signal_callbacks:
            try:
                callback(signal, details)
            except Exception as e:
                logger.error(f"Erreur callback signal: {e}")
    
    def _trigger_trade_callbacks(self, trade: ActiveTrade, event: str):
        """Déclenche les callbacks de trade"""
        for callback in self.on_trade_callbacks:
            try:
                callback(trade, event)
            except Exception as e:
                logger.error(f"Erreur callback trade: {e}")
    
    def _trigger_alert_callbacks(self, alert: Alert):
        """Déclenche les callbacks d'alerte"""
        for callback in self.on_alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Erreur callback alerte: {e}")
    
    def get_statistics(self) -> TradingStatistics:
        """Retourne les statistiques"""
        self.statistics.calculate_from_trades(self.closed_trades)
        return self.statistics
    
    def get_active_trades(self) -> List[ActiveTrade]:
        """Retourne les trades actifs"""
        return list(self.active_trades.values())
    
    def get_closed_trades(self) -> List[ActiveTrade]:
        """Retourne les trades fermés"""
        return self.closed_trades.copy()
    
    def get_alerts(self, limit: Optional[int] = None) -> List[Alert]:
        """Retourne les alertes"""
        alerts = self.alerts[-limit:] if limit else self.alerts
        return alerts.copy()
