"""
Modèles de données pour le bot CHARTIST
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum
import numpy as np


class PatternType(Enum):
    """Types de figures chartistes détectées"""
    HEAD_SHOULDERS = "head_shoulders"
    HEAD_SHOULDERS_INVERSE = "head_shoulders_inverse"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIANGLE_SYMMETRICAL = "triangle_symmetrical"
    TRIANGLE_ASCENDING = "triangle_ascending"
    TRIANGLE_DESCENDING = "triangle_descending"
    NONE = "none"


class TradeDirection(Enum):
    """Direction du trade"""
    LONG = "long"
    SHORT = "short"


class TradeStatus(Enum):
    """Statut d'un trade"""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


@dataclass
class Candlestick:
    """Structure représentant une chandelle"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int = 0
    
    @property
    def body(self) -> float:
        """Hauteur du corps de la chandelle"""
        return abs(self.close - self.open)
    
    @property
    def range(self) -> float:
        """Range total (High - Low)"""
        return self.high - self.low
    
    @property
    def upper_wick(self) -> float:
        """Mèche supérieure"""
        if self.close > self.open:
            return self.high - self.close
        else:
            return self.high - self.open
    
    @property
    def lower_wick(self) -> float:
        """Mèche inférieure"""
        if self.close > self.open:
            return self.open - self.low
        else:
            return self.close - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Chandelle haussière?"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Chandelle baissière?"""
        return self.close < self.open


@dataclass
class PatternSignal:
    """Signal de figure détectée"""
    pattern_type: PatternType
    timestamp: datetime
    pair: str
    timeframe: str
    direction: TradeDirection
    
    # Points clés du pattern
    start_index: int
    end_index: int
    pattern_start_price: float
    pattern_end_price: float
    
    # Niveaux
    entry_level: float
    resistance_level: float
    support_level: float
    
    # Confirmation
    multi_tf_confirmed: bool = False
    pullback_confirmed: bool = False
    atr_confirmed: bool = False
    confidence_score: float = 0.0
    
    # Métadonnées
    detected_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    

@dataclass
class TradeSetup:
    """Configuration complète pour un trade"""
    signal: PatternSignal
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float  # En contrats ou unités
    risk_amount: float    # En devise
    reward_amount: float
    risk_reward_ratio: float
    
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ActiveTrade:
    """Trade actif en cours"""
    id: str
    pair: str
    timeframe: str
    direction: TradeDirection
    
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    
    entry_time: datetime
    exit_time: Optional[datetime] = None
    
    current_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    
    status: TradeStatus = TradeStatus.OPEN
    exit_reason: Optional[str] = None
    
    # Historique
    high_price: float = 0.0
    low_price: float = 0.0
    

@dataclass
class TradingStatistics:
    """Statistiques de trading"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_profit: float = 0.0
    
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    
    max_drawdown: float = 0.0
    max_drawdown_percent: float = 0.0
    
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    
    best_trade: float = 0.0
    worst_trade: float = 0.0
    
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    max_consecutive_losses: int = 0
    
    def calculate_from_trades(self, trades: List[ActiveTrade]):
        """Calcule les stats à partir d'une liste de trades"""
        if not trades:
            return
        
        closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED]
        self.total_trades = len(closed_trades)
        
        if self.total_trades == 0:
            return
        
        winning = [t for t in closed_trades if t.pnl > 0]
        losing = [t for t in closed_trades if t.pnl < 0]
        
        self.winning_trades = len(winning)
        self.losing_trades = len(losing)
        self.win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        self.gross_profit = sum(t.pnl for t in winning)
        self.gross_loss = abs(sum(t.pnl for t in losing))
        self.net_profit = sum(t.pnl for t in closed_trades)
        
        self.avg_win = self.gross_profit / self.winning_trades if self.winning_trades > 0 else 0
        self.avg_loss = self.gross_loss / self.losing_trades if self.losing_trades > 0 else 0
        
        if self.gross_loss > 0:
            self.profit_factor = self.gross_profit / self.gross_loss
        
        pnls = [t.pnl for t in closed_trades]
        if pnls:
            self.best_trade = max(pnls)
            self.worst_trade = min(pnls)


@dataclass
class Alert:
    """Alerte du bot"""
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR, CRITICAL
    message: str
    pair: Optional[str] = None
    trade_id: Optional[str] = None
    
    def __str__(self) -> str:
        pair_str = f" [{self.pair}]" if self.pair else ""
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {self.level}{pair_str}: {self.message}"
