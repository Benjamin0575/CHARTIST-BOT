"""
Système de confirmation pour les signaux
Multi-timeframe, Pullback, et ATR
"""
import logging
from typing import List, Optional, Tuple
import numpy as np

from models import Candlestick, PatternSignal


logger = logging.getLogger(__name__)


class ATRCalculator:
    """Calcule l'ATR (Average True Range) pour la volatilité"""
    
    @staticmethod
    def calculate_atr(candles: List[Candlestick], period: int = 14) -> Optional[float]:
        """
        Calcule l'ATR
        
        Args:
            candles: Liste des candlesticks
            period: Période de calcul
        
        Returns:
            Valeur ATR ou None
        """
        if len(candles) < period:
            return None
        
        tr_values = []
        
        for i in range(len(candles)):
            if i == 0:
                tr = candles[i].high - candles[i].low
            else:
                hl = candles[i].high - candles[i].low
                hc = abs(candles[i].high - candles[i - 1].close)
                lc = abs(candles[i].low - candles[i - 1].close)
                tr = max(hl, hc, lc)
            
            tr_values.append(tr)
        
        # ATR = moyenne mobile exponentielle du TR
        atr = np.mean(tr_values[-period:])
        return atr
    
    @staticmethod
    def get_volatility_level(atr: float, current_price: float) -> str:
        """
        Détermine le niveau de volatilité
        
        Returns:
            "low", "medium", "high"
        """
        atr_percent = (atr / current_price) * 100
        
        if atr_percent < 0.5:
            return "low"
        elif atr_percent < 1.5:
            return "medium"
        else:
            return "high"


class PullbackDetector:
    """Détecte les pullbacks dans les patterns"""
    
    @staticmethod
    def detect_pullback(candles: List[Candlestick], pattern_signal: PatternSignal,
                       pullback_percent: float = 38.2) -> Tuple[bool, Optional[float]]:
        """
        Détecte si un pullback valide s'est produit après le pattern
        
        Args:
            candles: Liste des candlesticks
            pattern_signal: Le signal du pattern
            pullback_percent: % de retracement de Fibonacci à chercher
        
        Returns:
            (pullback_détecté, niveau_pullback)
        """
        if len(candles) < 5:
            return False, None
        
        # Prendre les dernières candlesticks après le pattern
        recent = candles[-5:]
        
        # Direction du trend initial
        if pattern_signal.direction.value == "short":
            # Pattern bearish: chercher un pullback vers le haut
            recent_low = min(c.low for c in recent)
            recent_high = max(c.high for c in recent)
            
            # Pullback doit être une remontée partielle
            range_size = pattern_signal.pattern_start_price - pattern_signal.support_level
            pullback_level = pattern_signal.pattern_start_price - (range_size * pullback_percent / 100)
            
            # Vérifier que ça a remonté mais pas trop
            if recent_high > pullback_level and recent_low < pattern_signal.pattern_start_price:
                return True, recent_high
        
        else:  # LONG
            # Pattern bullish: chercher un pullback vers le bas
            recent_low = min(c.low for c in recent)
            recent_high = max(c.high for c in recent)
            
            range_size = pattern_signal.resistance_level - pattern_signal.pattern_start_price
            pullback_level = pattern_signal.pattern_start_price + (range_size * pullback_percent / 100)
            
            if recent_low < pullback_level and recent_high > pattern_signal.pattern_start_price:
                return True, recent_low
        
        return False, None
    
    @staticmethod
    def get_fibonacci_levels(high: float, low: float) -> dict:
        """
        Calcule les niveaux de retracement Fibonacci
        
        Returns:
            Dict avec les niveaux (23.6%, 38.2%, 50%, 61.8%, 78.6%)
        """
        range_size = high - low
        
        return {
            "23.6": high - (range_size * 0.236),
            "38.2": high - (range_size * 0.382),
            "50.0": high - (range_size * 0.500),
            "61.8": high - (range_size * 0.618),
            "78.6": high - (range_size * 0.786)
        }


class MultiTimeframeConfirmation:
    """Confirme les signaux sur plusieurs timeframes"""
    
    @staticmethod
    def is_confirmed(signal_tf: str, trend_tf: str, trend_direction: str,
                    signal_direction: str) -> bool:
        """
        Vérifie si le signal est confirmé par le timeframe supérieur
        
        Args:
            signal_tf: Timeframe du signal (ex: "5m")
            trend_tf: Timeframe du trend confirmant (ex: "15m")
            trend_direction: Direction du trend ("up" ou "down")
            signal_direction: Direction du signal ("long" ou "short")
        
        Returns:
            True si confirmé
        """
        # Plus le trend est dans le même sens que le signal, mieux c'est
        if signal_direction == "long":
            return trend_direction == "up"
        else:
            return trend_direction == "down"
    
    @staticmethod
    def determine_trend(candles: List[Candlestick], period: int = 20) -> str:
        """
        Détermine la direction du trend
        
        Args:
            candles: Candlesticks
            period: Période pour calculer SMA
        
        Returns:
            "up", "down", ou "sideways"
        """
        if len(candles) < period:
            return "sideways"
        
        closes = [c.close for c in candles]
        sma = np.mean(closes[-period:])
        current_close = closes[-1]
        
        # Calculer la pente aussi
        recent_candles = candles[-period:]
        first_close = recent_candles[0].close
        last_close = recent_candles[-1].close
        
        change_percent = ((last_close - first_close) / first_close) * 100
        
        if change_percent > 0.5:
            return "up"
        elif change_percent < -0.5:
            return "down"
        else:
            return "sideways"


class ConfirmationSystem:
    """Système complet de confirmation des signaux"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration du système (voir config.json)
        """
        self.multi_tf_enabled = config.get("multi_timeframe", True)
        self.pullback_required = config.get("pullback_required", True)
        self.pullback_percent = config.get("pullback_percent", 38.2)
        self.atr_multiplier = config.get("atr_multiplier", 1.5)
    
    def confirm_signal(self, signal: PatternSignal,
                      candles_tf1: List[Candlestick],
                      candles_tf2: Optional[List[Candlestick]] = None) -> Tuple[bool, dict]:
        """
        Confirme un signal complet
        
        Args:
            signal: Le pattern signal
            candles_tf1: Candlesticks du timeframe du signal
            candles_tf2: Candlesticks du timeframe supérieur (optionnel)
        
        Returns:
            (confirmé, détails_confirmation)
        """
        confirmation_details = {
            "multi_tf_confirmed": False,
            "pullback_confirmed": False,
            "atr_confirmed": False,
            "final_confidence": 0.0
        }
        
        # 1. Pullback confirmation
        if self.pullback_required:
            pullback_ok, pullback_level = PullbackDetector.detect_pullback(
                candles_tf1, signal, self.pullback_percent
            )
            confirmation_details["pullback_confirmed"] = pullback_ok
            confirmation_details["pullback_level"] = pullback_level
        else:
            confirmation_details["pullback_confirmed"] = True
        
        # 2. ATR confirmation
        atr = ATRCalculator.calculate_atr(candles_tf1)
        if atr:
            atr_ok = self._verify_atr(signal, atr)
            confirmation_details["atr_confirmed"] = atr_ok
            confirmation_details["atr_value"] = atr
        else:
            confirmation_details["atr_confirmed"] = True
        
        # 3. Multi-timeframe confirmation
        if self.multi_tf_enabled and candles_tf2:
            trend = MultiTimeframeConfirmation.determine_trend(candles_tf2)
            signal_dir = signal.direction.value
            
            mtf_confirmed = MultiTimeframeConfirmation.is_confirmed(
                signal.timeframe, "15m", trend, signal_dir
            )
            confirmation_details["multi_tf_confirmed"] = mtf_confirmed
            confirmation_details["trend_tf2"] = trend
        else:
            confirmation_details["multi_tf_confirmed"] = True
        
        # 4. Score final
        confirmation_score = signal.confidence_score
        
        if confirmation_details["pullback_confirmed"]:
            confirmation_score += 0.1
        
        if confirmation_details["atr_confirmed"]:
            confirmation_score += 0.1
        
        if confirmation_details["multi_tf_confirmed"]:
            confirmation_score += 0.1
        
        confirmation_score = min(confirmation_score, 1.0)
        confirmation_details["final_confidence"] = confirmation_score
        
        # Signal confirmé si tous les critères sont ok
        all_confirmed = (
            confirmation_details["pullback_confirmed"] and
            confirmation_details["atr_confirmed"] and
            confirmation_details["multi_tf_confirmed"] and
            confirmation_score > 0.65
        )
        
        logger.info(f"Signal {signal.pattern_type.value} - Confirmation: {all_confirmed} "
                   f"(confidence: {confirmation_score:.2f})")
        
        return all_confirmed, confirmation_details
    
    def _verify_atr(self, signal: PatternSignal, atr: float) -> bool:
        """
        Vérifie que l'ATR est cohérent avec le pattern
        """
        # L'ATR doit être raisonnablement petit comparé à la taille du pattern
        pattern_range = abs(signal.resistance_level - signal.support_level)
        
        # ATR ne doit pas être > 1.5x la range du pattern
        return atr < pattern_range * self.atr_multiplier
