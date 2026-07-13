"""
Détecteur de figures chartistes
Reconnaît: Head & Shoulders, Double Top/Bottom, Triangles
"""
import logging
from typing import List, Optional, Tuple
from datetime import datetime
import numpy as np

from models import Candlestick, PatternSignal, PatternType, TradeDirection


logger = logging.getLogger(__name__)


class PatternDetector:
    """Détecte les figures chartistes dans les données OHLC"""
    
    def __init__(self, sensitivity: str = "medium", lookback: int = 50):
        """
        Args:
            sensitivity: "low", "medium", "high"
            lookback: Nombre de candlesticks à analyser
        """
        self.sensitivity = sensitivity
        self.lookback = lookback
        
        # Paramètres de sensibilité
        self.sensitivity_params = {
            "low": {"tolerance": 0.02, "min_range": 0.015},
            "medium": {"tolerance": 0.015, "min_range": 0.010},
            "high": {"tolerance": 0.010, "min_range": 0.005}
        }
        
        self.params = self.sensitivity_params.get(sensitivity, self.sensitivity_params["medium"])
    
    def detect(self, candles: List[Candlestick], pair: str, timeframe: str) -> List[PatternSignal]:
        """
        Détecte tous les patterns dans les candlesticks
        
        Args:
            candles: Liste des candlesticks
            pair: Symbole de la paire
            timeframe: Intervalle temporel
        
        Returns:
            Liste des signaux détectés
        """
        if len(candles) < 10:
            return []
        
        signals = []
        
        # Analyser les dernières candlesticks
        to_analyze = candles[-self.lookback:]
        
        # Détecteurs
        signals.extend(self._detect_head_shoulders(to_analyze, pair, timeframe))
        signals.extend(self._detect_double_top_bottom(to_analyze, pair, timeframe))
        signals.extend(self._detect_triangles(to_analyze, pair, timeframe))
        
        return signals
    
    # ==================== HEAD & SHOULDERS ====================
    
    def _detect_head_shoulders(self, candles: List[Candlestick], pair: str, 
                               timeframe: str) -> List[PatternSignal]:
        """Détecte Head & Shoulders (normal et inverse)"""
        signals = []
        
        if len(candles) < 15:
            return signals
        
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        
        # Chercher 3 pics (head & shoulders normal)
        for i in range(5, len(candles) - 5):
            # Left shoulder
            if not self._is_local_extremum(highs, i - 5, "high"):
                continue
            
            left_shoulder_high = highs[i - 5]
            left_shoulder_idx = i - 5
            
            # Head (plus haut que les deux épaules)
            head_idx = self._find_next_local_extremum(highs, i, i + 5, "high")
            if head_idx is None:
                continue
            
            head_high = highs[head_idx]
            
            # Right shoulder
            right_shoulder_idx = self._find_next_local_extremum(highs, head_idx, head_idx + 5, "high")
            if right_shoulder_idx is None:
                continue
            
            right_shoulder_high = highs[right_shoulder_idx]
            
            # Vérifications
            if not (head_high > left_shoulder_high * (1 + self.params["tolerance"]) and
                    head_high > right_shoulder_high * (1 + self.params["tolerance"])):
                continue
            
            if not (abs(left_shoulder_high - right_shoulder_high) < left_shoulder_high * self.params["tolerance"]):
                continue
            
            # Neckline (support)
            neckline = self._estimate_neckline(closes[left_shoulder_idx:right_shoulder_idx + 1])
            
            if head_high <= neckline:
                continue
            
            # Pattern valide
            entry = neckline
            target = head_high - (head_high - neckline)
            
            signal = PatternSignal(
                pattern_type=PatternType.HEAD_SHOULDERS,
                timestamp=datetime.now(),
                pair=pair,
                timeframe=timeframe,
                direction=TradeDirection.SHORT,
                start_index=left_shoulder_idx,
                end_index=right_shoulder_idx,
                pattern_start_price=left_shoulder_high,
                pattern_end_price=right_shoulder_high,
                entry_level=neckline,
                resistance_level=head_high,
                support_level=target,
                confidence_score=0.7
            )
            
            signals.append(signal)
        
        return signals
    
    # ==================== DOUBLE TOP/BOTTOM ====================
    
    def _detect_double_top_bottom(self, candles: List[Candlestick], pair: str,
                                  timeframe: str) -> List[PatternSignal]:
        """Détecte Double Top et Double Bottom"""
        signals = []
        
        if len(candles) < 12:
            return signals
        
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        closes = [c.close for c in candles]
        
        # Double Top (2 pics à peu près au même niveau)
        for i in range(5, len(candles) - 5):
            first_top_idx = self._find_local_maximum(highs, max(0, i - 8), i)
            if first_top_idx is None:
                continue
            
            first_top = highs[first_top_idx]
            
            # Trouver le deuxième pic
            second_top_idx = self._find_local_maximum(highs, i, min(len(candles), i + 8))
            if second_top_idx is None:
                continue
            
            second_top = highs[second_top_idx]
            
            # Les deux pics doivent être proches en prix
            if abs(first_top - second_top) > first_top * self.params["tolerance"]:
                continue
            
            # Support entre les deux (valley)
            valley_idx = self._find_local_minimum(lows, first_top_idx, second_top_idx)
            if valley_idx is None:
                continue
            
            valley = lows[valley_idx]
            
            # Pattern valide
            entry = valley
            target = valley - (first_top - valley)
            
            signal = PatternSignal(
                pattern_type=PatternType.DOUBLE_TOP,
                timestamp=datetime.now(),
                pair=pair,
                timeframe=timeframe,
                direction=TradeDirection.SHORT,
                start_index=first_top_idx,
                end_index=second_top_idx,
                pattern_start_price=first_top,
                pattern_end_price=second_top,
                entry_level=entry,
                resistance_level=max(first_top, second_top),
                support_level=target,
                confidence_score=0.65
            )
            
            signals.append(signal)
        
        # Double Bottom (inversé)
        for i in range(5, len(candles) - 5):
            first_bottom_idx = self._find_local_minimum(lows, max(0, i - 8), i)
            if first_bottom_idx is None:
                continue
            
            first_bottom = lows[first_bottom_idx]
            
            second_bottom_idx = self._find_local_minimum(lows, i, min(len(candles), i + 8))
            if second_bottom_idx is None:
                continue
            
            second_bottom = lows[second_bottom_idx]
            
            if abs(first_bottom - second_bottom) > first_bottom * self.params["tolerance"]:
                continue
            
            peak_idx = self._find_local_maximum(highs, first_bottom_idx, second_bottom_idx)
            if peak_idx is None:
                continue
            
            peak = highs[peak_idx]
            
            entry = peak
            target = peak + (peak - first_bottom)
            
            signal = PatternSignal(
                pattern_type=PatternType.DOUBLE_BOTTOM,
                timestamp=datetime.now(),
                pair=pair,
                timeframe=timeframe,
                direction=TradeDirection.LONG,
                start_index=first_bottom_idx,
                end_index=second_bottom_idx,
                pattern_start_price=first_bottom,
                pattern_end_price=second_bottom,
                entry_level=entry,
                resistance_level=target,
                support_level=min(first_bottom, second_bottom),
                confidence_score=0.65
            )
            
            signals.append(signal)
        
        return signals
    
    # ==================== TRIANGLES ====================
    
    def _detect_triangles(self, candles: List[Candlestick], pair: str,
                         timeframe: str) -> List[PatternSignal]:
        """Détecte Triangles (Symmetrique, Ascendant, Descendant)"""
        signals = []
        
        if len(candles) < 15:
            return signals
        
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        # Chercher des triangles
        for start_idx in range(5, len(candles) - 10):
            segment = candles[start_idx:start_idx + 12]
            
            # Analyser les highs et lows pour détecter convergence
            seg_highs = [c.high for c in segment]
            seg_lows = [c.low for c in segment]
            
            # Trouver les extremums locaux
            peaks = self._find_local_maxima(seg_highs)
            troughs = self._find_local_minima(seg_lows)
            
            if len(peaks) < 2 or len(troughs) < 2:
                continue
            
            # Vérifier la convergence (triangle)
            first_range = seg_highs[0] - seg_lows[0]
            last_range = seg_highs[-1] - seg_lows[-1]
            
            if last_range >= first_range * 0.7:  # Range doit diminuer
                continue
            
            # Déterminer le type de triangle
            triangle_type = self._classify_triangle(seg_highs, seg_lows)
            
            if triangle_type is None:
                continue
            
            # Pattern détecté
            breakout_level = seg_highs[-1] if triangle_type in [PatternType.TRIANGLE_ASCENDING, PatternType.TRIANGLE_SYMMETRICAL] else seg_lows[-1]
            
            direction = TradeDirection.LONG if triangle_type in [PatternType.TRIANGLE_ASCENDING, PatternType.TRIANGLE_SYMMETRICAL] else TradeDirection.SHORT
            
            signal = PatternSignal(
                pattern_type=triangle_type,
                timestamp=datetime.now(),
                pair=pair,
                timeframe=timeframe,
                direction=direction,
                start_index=start_idx,
                end_index=start_idx + len(segment) - 1,
                pattern_start_price=seg_highs[0],
                pattern_end_price=seg_highs[-1],
                entry_level=breakout_level,
                resistance_level=max(seg_highs),
                support_level=min(seg_lows),
                confidence_score=0.60
            )
            
            signals.append(signal)
        
        return signals
    
    # ==================== HELPERS ====================
    
    def _is_local_extremum(self, prices: List[float], idx: int, extremum_type: str) -> bool:
        """Vérifie si c'est un extremum local"""
        if idx < 1 or idx >= len(prices) - 1:
            return False
        
        if extremum_type == "high":
            return prices[idx] > prices[idx - 1] and prices[idx] > prices[idx + 1]
        else:  # low
            return prices[idx] < prices[idx - 1] and prices[idx] < prices[idx + 1]
    
    def _find_next_local_extremum(self, prices: List[float], start: int, end: int, 
                                 extremum_type: str) -> Optional[int]:
        """Trouve le prochain extremum local"""
        for i in range(start, min(end, len(prices) - 1)):
            if self._is_local_extremum(prices, i, extremum_type):
                return i
        return None
    
    def _find_local_maximum(self, prices: List[float], start: int, end: int) -> Optional[int]:
        """Trouve le maximum local dans une plage"""
        max_idx = None
        max_val = float('-inf')
        
        for i in range(max(0, start), min(len(prices), end)):
            if self._is_local_extremum(prices, i, "high") and prices[i] > max_val:
                max_idx = i
                max_val = prices[i]
        
        return max_idx
    
    def _find_local_minimum(self, prices: List[float], start: int, end: int) -> Optional[int]:
        """Trouve le minimum local dans une plage"""
        min_idx = None
        min_val = float('inf')
        
        for i in range(max(0, start), min(len(prices), end)):
            if self._is_local_extremum(prices, i, "low") and prices[i] < min_val:
                min_idx = i
                min_val = prices[i]
        
        return min_idx
    
    def _find_local_maxima(self, prices: List[float]) -> List[int]:
        """Trouve tous les maxima locaux"""
        maxima = []
        for i in range(1, len(prices) - 1):
            if prices[i] > prices[i - 1] and prices[i] > prices[i + 1]:
                maxima.append(i)
        return maxima
    
    def _find_local_minima(self, prices: List[float]) -> List[int]:
        """Trouve tous les minima locaux"""
        minima = []
        for i in range(1, len(prices) - 1):
            if prices[i] < prices[i - 1] and prices[i] < prices[i + 1]:
                minima.append(i)
        return minima
    
    def _estimate_neckline(self, closes: List[float]) -> float:
        """Estime la neckline (moyenne des bas)"""
        return sum(closes) / len(closes) if closes else 0
    
    def _classify_triangle(self, highs: List[float], lows: List[float]) -> Optional[PatternType]:
        """Classifie le type de triangle"""
        if len(highs) < 4 or len(lows) < 4:
            return None
        
        # Calculer les pentes
        high_slope = (highs[-1] - highs[0]) / len(highs)
        low_slope = (lows[-1] - lows[0]) / len(lows)
        
        # Tolérance pour classification
        threshold = (highs[0] - lows[0]) * 0.02
        
        # Triangle symétrique: highs baissent, lows montent
        if high_slope < -threshold and low_slope > threshold:
            return PatternType.TRIANGLE_SYMMETRICAL
        
        # Triangle ascendant: highs stables/montants, lows montent
        elif high_slope > -threshold and low_slope > threshold:
            return PatternType.TRIANGLE_ASCENDING
        
        # Triangle descendant: highs baissent, lows stables/baissants
        elif high_slope < -threshold and low_slope < threshold:
            return PatternType.TRIANGLE_DESCENDING
        
        return None
