"""
Gestionnaire de risque et sizing des positions
"""
import logging
from typing import Optional, Tuple
import numpy as np

from models import Candlestick, PatternSignal, TradeSetup


logger = logging.getLogger(__name__)


class RiskManager:
    """Gère le risque et le sizing des positions"""
    
    def __init__(self, account_balance: float, risk_percent: float = 1.5,
                 max_daily_loss_percent: float = 5.0):
        """
        Args:
            account_balance: Solde du compte de trading
            risk_percent: % de risque par trade (1.5% = 0.015)
            max_daily_loss_percent: Max drawdown journalier autorisé
        """
        self.account_balance = account_balance
        self.risk_percent = risk_percent / 100  # Convertir en décimal
        self.max_daily_loss_percent = max_daily_loss_percent / 100
        
        self.daily_loss = 0.0
        self.trades_today = 0
        self.max_concurrent_positions = 3
        self.active_trades_count = 0
    
    def calculate_position_size(self, signal: PatternSignal, atr: Optional[float] = None,
                               min_tick_size: float = 0.01) -> Tuple[float, float, float]:
        """
        Calcule la taille de la position
        
        Args:
            signal: Le pattern signal
            atr: ATR pour ajuster le stop loss (optionnel)
            min_tick_size: Taille minimum de tick
        
        Returns:
            (position_size, risk_amount, entry_price)
        """
        # Calcul basique: risque fixe par trade
        risk_amount = self.account_balance * self.risk_percent
        
        # Distance stop loss - entry
        if atr:
            # Utiliser ATR pour déterminer le stop loss
            stop_distance = atr * 1.2  # ATR x 1.2
        else:
            # Utiliser la distance du pattern
            pattern_range = abs(signal.resistance_level - signal.support_level)
            stop_distance = pattern_range * 0.5
        
        # Position size = Risk / Distance
        position_size = risk_amount / stop_distance if stop_distance > 0 else 0
        
        # Limiter la taille (max 5% du compte)
        max_position_value = self.account_balance * 0.05
        position_size = min(position_size, max_position_value / signal.entry_level)
        
        return position_size, risk_amount, signal.entry_level
    
    def set_tp_sl(self, signal: PatternSignal, atr: Optional[float] = None,
                 min_risk_reward_ratio: float = 1.5) -> Tuple[float, float, float]:
        """
        Définit Take Profit et Stop Loss
        
        Args:
            signal: Pattern signal
            atr: ATR pour ajustement dynamique
            min_risk_reward_ratio: Ratio R:R minimum (ex: 1.5)
        
        Returns:
            (entry_price, stop_loss, take_profit)
        """
        entry = signal.entry_level
        
        if atr:
            # TP/SL basés sur ATR
            if signal.direction.value == "long":
                stop_loss = entry - (atr * 1.2)
                take_profit = entry + (atr * 2.5)  # R:R > 1.5
            else:  # SHORT
                stop_loss = entry + (atr * 1.2)
                take_profit = entry - (atr * 2.5)
        else:
            # TP/SL basés sur la structure du pattern
            if signal.direction.value == "long":
                stop_loss = signal.support_level
                take_profit = signal.resistance_level + (signal.resistance_level - signal.support_level) * 0.5
            else:  # SHORT
                stop_loss = signal.resistance_level
                take_profit = signal.support_level - (signal.resistance_level - signal.support_level) * 0.5
        
        # Vérifier le ratio R:R
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        
        if risk > 0:
            rr_ratio = reward / risk
            
            if rr_ratio < min_risk_reward_ratio:
                # Ajuster TP pour respecter le ratio
                if signal.direction.value == "long":
                    take_profit = entry + (risk * min_risk_reward_ratio)
                else:
                    take_profit = entry - (risk * min_risk_reward_ratio)
                
                logger.info(f"TP ajusté pour respecter R:R {min_risk_reward_ratio}")
        
        return entry, stop_loss, take_profit
    
    def can_open_trade(self) -> bool:
        """Vérifie si une trade peut être ouverte"""
        # Vérifier le nombre de trades concurrentes
        if self.active_trades_count >= self.max_concurrent_positions:
            logger.warning(f"Max positions ({self.max_concurrent_positions}) atteint")
            return False
        
        # Vérifier la perte journalière
        daily_loss_limit = self.account_balance * self.max_daily_loss_percent
        if self.daily_loss >= daily_loss_limit:
            logger.warning(f"Perte journalière max ({daily_loss_limit}) atteinte")
            return False
        
        return True
    
    def record_trade_loss(self, loss: float):
        """Enregistre une perte de trade"""
        if loss > 0:
            self.daily_loss += loss
    
    def update_account_balance(self, new_balance: float):
        """Met à jour le solde du compte"""
        self.account_balance = new_balance
    
    def reset_daily_stats(self):
        """Réinitialise les stats journalières"""
        self.daily_loss = 0.0
        self.trades_today = 0


class KellyCriterion:
    """Implémente le Kelly Criterion pour le sizing optimal"""
    
    @staticmethod
    def calculate_kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calcule la fraction de Kelly
        
        Args:
            win_rate: % de wins (0-1)
            avg_win: Gain moyen
            avg_loss: Perte moyenne
        
        Returns:
            Fraction de Kelly (typiquement 0.01-0.03 pour les traders)
        """
        if avg_loss == 0:
            return 0
        
        loss_rate = 1 - win_rate
        
        kelly_fraction = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        
        # Kelly peut être agressif, donc utiliser une fraction
        # Généralement on utilise 25-50% de Kelly pour la sécurité
        kelly_fraction = max(kelly_fraction, 0)
        kelly_fraction = min(kelly_fraction, 0.25)  # Max 25% de Kelly
        
        return kelly_fraction


class PositionManager:
    """Gère les positions ouvertes"""
    
    def __init__(self):
        self.open_positions = {}  # id -> position
        self.closed_positions = {}
    
    def add_position(self, trade_id: str, position_data: dict):
        """Ajoute une position ouverte"""
        self.open_positions[trade_id] = position_data
    
    def close_position(self, trade_id: str, exit_price: float, exit_reason: str):
        """Ferme une position"""
        if trade_id in self.open_positions:
            position = self.open_positions[trade_id]
            position['exit_price'] = exit_price
            position['exit_reason'] = exit_reason
            position['pnl'] = self._calculate_pnl(position, exit_price)
            
            self.closed_positions[trade_id] = position
            del self.open_positions[trade_id]
            
            return position
        return None
    
    def get_open_positions(self) -> dict:
        """Retourne les positions ouvertes"""
        return self.open_positions.copy()
    
    def get_position_by_id(self, trade_id: str) -> Optional[dict]:
        """Récupère une position par ID"""
        return self.open_positions.get(trade_id)
    
    def update_position(self, trade_id: str, **kwargs):
        """Met à jour une position"""
        if trade_id in self.open_positions:
            self.open_positions[trade_id].update(kwargs)
    
    def _calculate_pnl(self, position: dict, exit_price: float) -> float:
        """Calcule le PnL d'une position"""
        entry_price = position['entry_price']
        position_size = position['position_size']
        direction = position['direction']
        
        if direction == "long":
            return (exit_price - entry_price) * position_size
        else:  # short
            return (entry_price - exit_price) * position_size


class DrawdownTracker:
    """Suit les drawdowns"""
    
    def __init__(self):
        self.peak_balance = 0
        self.current_balance = 0
        self.max_drawdown = 0
        self.max_drawdown_percent = 0
    
    def update(self, current_balance: float):
        """Met à jour le drawdown"""
        self.current_balance = current_balance
        
        # Actualiser le peak
        if current_balance > self.peak_balance:
            self.peak_balance = current_balance
        
        # Calculer le drawdown actuel
        if self.peak_balance > 0:
            drawdown = self.peak_balance - current_balance
            drawdown_percent = (drawdown / self.peak_balance) * 100
            
            # Actualiser les max
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            if drawdown_percent > self.max_drawdown_percent:
                self.max_drawdown_percent = drawdown_percent
    
    def get_current_drawdown(self) -> Tuple[float, float]:
        """Retourne le drawdown actuel (montant, %)"""
        if self.peak_balance > 0:
            drawdown = self.peak_balance - self.current_balance
            drawdown_percent = (drawdown / self.peak_balance) * 100
            return drawdown, drawdown_percent
        return 0, 0
