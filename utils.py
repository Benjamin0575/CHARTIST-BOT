"""
Utilitaires et fonctions helper pour le bot
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np

from models import ActiveTrade, Candlestick


logger = logging.getLogger(__name__)


class FormatUtils:
    """Utilitaires de formatage"""
    
    @staticmethod
    def format_price(price: float, decimals: int = 5) -> str:
        """Formate un prix"""
        return f"{price:.{decimals}f}"
    
    @staticmethod
    def format_percent(value: float, decimals: int = 2) -> str:
        """Formate un pourcentage"""
        return f"{value:+.{decimals}f}%"
    
    @staticmethod
    def format_currency(amount: float, symbol: str = "USD") -> str:
        """Formate une montant monétaire"""
        return f"{amount:,.2f} {symbol}"
    
    @staticmethod
    def format_time_elapsed(start: datetime, end: datetime) -> str:
        """Formate le temps écoulé"""
        delta = end - start
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        seconds = delta.seconds % 60
        
        if delta.days > 0:
            return f"{delta.days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @staticmethod
    def format_ratio(ratio: float, decimals: int = 2) -> str:
        """Formate un ratio"""
        return f"{ratio:.{decimals}f}:1"


class AnalysisUtils:
    """Utilitaires d'analyse"""
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> List[float]:
        """Calcule la SMA (Simple Moving Average)"""
        if len(prices) < period:
            return []
        
        sma = []
        for i in range(period - 1, len(prices)):
            avg = np.mean(prices[i - period + 1:i + 1])
            sma.append(avg)
        
        return sma
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> List[float]:
        """Calcule l'EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return []
        
        multiplier = 2 / (period + 1)
        ema = [np.mean(prices[:period])]
        
        for price in prices[period:]:
            ema.append(price * multiplier + ema[-1] * (1 - multiplier))
        
        return ema
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
        """Calcule l'RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return []
        
        deltas = np.diff(prices)
        seed = deltas[:period + 1]
        
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        rs = up / down if down != 0 else 0
        rsi = [100 - 100 / (1 + rs)]
        
        for delta in deltas[period + 1:]:
            if delta > 0:
                up = (up * (period - 1) + delta) / period
                down *= (period - 1) / period
            else:
                down = (down * (period - 1) - delta) / period
                up *= (period - 1) / period
            
            rs = up / down if down != 0 else 0
            rsi.append(100 - 100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_macd(prices: List[float]) -> Tuple[List[float], List[float], List[float]]:
        """Calcule MACD"""
        ema12 = AnalysisUtils.calculate_ema(prices, 12)
        ema26 = AnalysisUtils.calculate_ema(prices, 26)
        
        macd = [e12 - e26 for e12, e26 in zip(ema12, ema26)]
        signal = AnalysisUtils.calculate_ema(macd, 9)
        
        histogram = [m - s for m, s in zip(macd, signal)]
        
        return macd, signal, histogram


class StatisticsUtils:
    """Utilitaires statistiques"""
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calcule le Sharpe Ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (mean_return - risk_free_rate) / std_return
        return sharpe * np.sqrt(252)  # Annualisé
    
    @staticmethod
    def calculate_sortino_ratio(returns: List[float], target_return: float = 0.0) -> float:
        """Calcule le Sortino Ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        mean_return = np.mean(returns)
        
        # Downside deviation
        downside_returns = [r for r in returns if r < target_return]
        if not downside_returns:
            return float('inf')
        
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        sortino = (mean_return - target_return) / downside_std
        return sortino * np.sqrt(252)
    
    @staticmethod
    def calculate_max_drawdown(equity_curve: List[float]) -> Tuple[float, float]:
        """Calcule le Max Drawdown"""
        if not equity_curve:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = peak - value
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        return max_dd, max_dd_pct
    
    @staticmethod
    def calculate_win_rate(trades: List[ActiveTrade]) -> float:
        """Calcule le win rate"""
        if not trades:
            return 0.0
        
        wins = sum(1 for t in trades if t.pnl > 0)
        return (wins / len(trades)) * 100
    
    @staticmethod
    def calculate_profit_factor(trades: List[ActiveTrade]) -> float:
        """Calcule le profit factor"""
        if not trades:
            return 0.0
        
        gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss


class FileUtils:
    """Utilitaires fichiers"""
    
    @staticmethod
    def save_json(data: dict, filepath: str) -> bool:
        """Sauvegarde en JSON"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Erreur sauvegarde JSON: {e}")
            return False
    
    @staticmethod
    def load_json(filepath: str) -> dict:
        """Charge un JSON"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erreur lecture JSON: {e}")
            return {}
    
    @staticmethod
    def export_trades_csv(trades: List[ActiveTrade], filepath: str) -> bool:
        """Exporte les trades en CSV"""
        import csv
        
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'Paire', 'Direction', 'Entry Time', 'Exit Time',
                    'Entry Price', 'Exit Price', 'Position Size', 'PnL', 'PnL %',
                    'Raison Exit'
                ])
                
                for trade in trades:
                    writer.writerow([
                        trade.id,
                        trade.pair,
                        trade.direction.value,
                        trade.entry_time,
                        trade.exit_time or '',
                        f"{trade.entry_price:.5f}",
                        f"{trade.current_price:.5f}",
                        f"{trade.position_size:.2f}",
                        f"{trade.pnl:.2f}",
                        f"{trade.pnl_percent:.2f}",
                        trade.exit_reason or ''
                    ])
            
            return True
        except Exception as e:
            logger.error(f"Erreur export CSV: {e}")
            return False


class ValidationUtils:
    """Utilitaires validation"""
    
    @staticmethod
    def is_valid_price(price: float) -> bool:
        """Vérifie si un prix est valide"""
        return price > 0 and not np.isnan(price) and not np.isinf(price)
    
    @staticmethod
    def is_valid_position_size(size: float) -> bool:
        """Vérifie si une position size est valide"""
        return 0 < size < 1000000
    
    @staticmethod
    def is_valid_risk_percent(percent: float) -> bool:
        """Vérifie si un pourcentage de risque est valide"""
        return 0 < percent <= 5
    
    @staticmethod
    def validate_candlestick(candle: Candlestick) -> bool:
        """Valide une candlestick"""
        # High >= Low
        if candle.high < candle.low:
            return False
        
        # Open et Close entre High et Low
        if not (candle.low <= candle.open <= candle.high):
            return False
        
        if not (candle.low <= candle.close <= candle.high):
            return False
        
        # Tous les prix positifs
        if not all(ValidationUtils.is_valid_price(p) for p in 
                   [candle.open, candle.high, candle.low, candle.close]):
            return False
        
        return True


class TimeUtils:
    """Utilitaires temps"""
    
    @staticmethod
    def timeframe_to_minutes(timeframe: str) -> int:
        """Convertit un timeframe en minutes"""
        mapping = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        return mapping.get(timeframe, 0)
    
    @staticmethod
    def minutes_to_timeframe(minutes: int) -> str:
        """Convertit des minutes en timeframe"""
        mapping = {
            1: "1m",
            5: "5m",
            15: "15m",
            30: "30m",
            60: "1h",
            240: "4h",
            1440: "1d"
        }
        return mapping.get(minutes, "1h")
    
    @staticmethod
    def get_market_hours(timezone: str = "UTC") -> Tuple[int, int]:
        """Retourne les heures d'ouverture du marché"""
        # Deriv: H24 5j/7
        return 0, 24
    
    @staticmethod
    def is_market_open(timezone: str = "UTC") -> bool:
        """Vérifie si le marché est ouvert"""
        # Deriv est toujours ouvert
        return True
