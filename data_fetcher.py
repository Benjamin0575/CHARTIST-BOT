"""
Fetcher de données pour l'API Deriv
Gère la connexion websocket et la récupération des candlesticks
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from collections import defaultdict

import websocket
from threading import Thread, Lock

from models import Candlestick


logger = logging.getLogger(__name__)


class DerivDataFetcher:
    """Gestionnaire de données Deriv via WebSocket"""
    
    def __init__(self, app_id: str, api_token: str, api_endpoint: str = "wss://ws.derivws.com/websockets/v3"):
        self.app_id = app_id
        self.api_token = api_token
        self.api_endpoint = api_endpoint
        
        self.ws = None
        self.request_id = 0
        self.is_connected = False
        
        # Stockage des candlesticks
        self.candlesticks: Dict[str, Dict[str, List[Candlestick]]] = defaultdict(lambda: defaultdict(list))
        self.data_lock = Lock()
        
        # Callbacks pour nouvelles données
        self.on_candle_callbacks: List[Callable] = []
        self.on_connection_callbacks: List[Callable] = []
        
        # Subscriptions actives
        self.subscriptions: Dict[int, Dict] = {}
        
    def connect(self):
        """Établit la connexion WebSocket"""
        try:
            logger.info("Connexion à Deriv...")
            self.ws = websocket.WebSocketApp(
                self.api_endpoint,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Exécute la connexion dans un thread séparé
            ws_thread = Thread(target=self.ws.run_forever, daemon=True)
            ws_thread.start()
            
            # Attendre la connexion
            for _ in range(30):
                if self.is_connected:
                    logger.info("✓ Connecté à Deriv")
                    return True
                asyncio.sleep(0.1)
            
            logger.error("Timeout lors de la connexion à Deriv")
            return False
            
        except Exception as e:
            logger.error(f"Erreur de connexion: {e}")
            return False
    
    def _on_open(self, ws):
        """Callback de connexion établie"""
        logger.info("WebSocket ouvert")
        self._authorize()
    
    def _authorize(self):
        """S'authentifie auprès de Deriv"""
        auth_msg = {
            "authorize": self.api_token,
            "req_id": self._get_request_id()
        }
        self.ws.send(json.dumps(auth_msg))
    
    def _on_message(self, ws, message):
        """Traite les messages reçus"""
        try:
            data = json.loads(message)
            
            # Vérifier l'authentification
            if 'authorize' in data:
                if data.get('authorize'):
                    self.is_connected = True
                    logger.info("✓ Authentification réussie")
                    self._trigger_connection_callbacks()
                else:
                    logger.error(f"Erreur d'authentification: {data.get('error')}")
            
            # Traiter les données de candlesticks
            elif 'candles' in data:
                self._process_candles(data)
            
            # Traiter les ticks/mises à jour
            elif 'tick' in data:
                self._process_tick(data)
                
        except Exception as e:
            logger.error(f"Erreur traitement message: {e}")
    
    def _on_error(self, ws, error):
        """Callback erreur"""
        logger.error(f"WebSocket erreur: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Callback fermeture"""
        logger.warning(f"WebSocket fermé: {close_msg}")
        self.is_connected = False
    
    def subscribe_candles(self, pair: str, timeframe: str = "5m"):
        """
        S'abonne aux candlesticks d'une paire
        
        Args:
            pair: Symbole de la paire (ex: "BOOM1000", "XAUUSD")
            timeframe: Intervalle en minutes (5, 15, 60, etc.)
        """
        if not self.is_connected:
            logger.error("Non connecté à Deriv")
            return False
        
        # Convertir timeframe en secondes
        tf_seconds = self._timeframe_to_seconds(timeframe)
        
        req_id = self._get_request_id()
        
        # Demander 200 dernières candlesticks pour avoir l'historique
        subscribe_msg = {
            "ticks_history": pair,
            "adjust_start_time": 1,
            "start": int((datetime.now() - timedelta(days=7)).timestamp()),
            "style": "candles",
            "granularity": tf_seconds,
            "count": 200,
            "req_id": req_id
        }
        
        self.subscriptions[req_id] = {
            "pair": pair,
            "timeframe": timeframe,
            "tf_seconds": tf_seconds
        }
        
        self.ws.send(json.dumps(subscribe_msg))
        logger.info(f"✓ Abonnement à {pair} {timeframe}")
        return True
    
    def unsubscribe(self, subscription_id: int):
        """Se désabonne"""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
    
    def _process_candles(self, data):
        """Traite les candlesticks reçues"""
        try:
            candles_data = data.get('candles', [])
            pair = data.get('symbol', '')
            
            if not candles_data or not pair:
                return
            
            req_id = data.get('req_id')
            if req_id not in self.subscriptions:
                return
            
            sub = self.subscriptions[req_id]
            timeframe = sub['timeframe']
            
            with self.data_lock:
                for candle in candles_data:
                    try:
                        ts = datetime.fromtimestamp(candle['epoch'])
                        ohlc = Candlestick(
                            timestamp=ts,
                            open=float(candle['open']),
                            high=float(candle['high']),
                            low=float(candle['low']),
                            close=float(candle['close']),
                            volume=int(candle.get('tick_count', 0))
                        )
                        
                        # Vérifier que la candelle n'existe pas déjà
                        existing = self.candlesticks[pair][timeframe]
                        if not existing or existing[-1].timestamp != ts:
                            self.candlesticks[pair][timeframe].append(ohlc)
                            
                    except Exception as e:
                        logger.error(f"Erreur parsing candelle: {e}")
                
                # Déclencher callbacks
                self._trigger_candle_callbacks(pair, timeframe)
                
        except Exception as e:
            logger.error(f"Erreur traitement candlesticks: {e}")
    
    def _process_tick(self, data):
        """Traite les ticks de mise à jour"""
        # À implémenter pour mises à jour temps réel
        pass
    
    def get_candles(self, pair: str, timeframe: str, limit: Optional[int] = None) -> List[Candlestick]:
        """
        Récupère les candlesticks stockées
        
        Args:
            pair: Symbole de la paire
            timeframe: Intervalle (ex: "5m", "15m")
            limit: Nombre max de candlesticks (None = toutes)
        
        Returns:
            Liste des candlesticks
        """
        with self.data_lock:
            candles = self.candlesticks.get(pair, {}).get(timeframe, [])
            if limit:
                return candles[-limit:]
            return candles.copy()
    
    def get_last_candle(self, pair: str, timeframe: str) -> Optional[Candlestick]:
        """Récupère la dernière candlestick"""
        candles = self.get_candles(pair, timeframe)
        return candles[-1] if candles else None
    
    def add_callback(self, callback: Callable, event_type: str = "candle"):
        """
        Ajoute un callback pour les événements
        
        Args:
            callback: Fonction à appeler
            event_type: "candle" ou "connection"
        """
        if event_type == "candle":
            self.on_candle_callbacks.append(callback)
        elif event_type == "connection":
            self.on_connection_callbacks.append(callback)
    
    def _trigger_candle_callbacks(self, pair: str, timeframe: str):
        """Déclenche les callbacks de candlesticks"""
        for callback in self.on_candle_callbacks:
            try:
                callback(pair, timeframe)
            except Exception as e:
                logger.error(f"Erreur callback candlestick: {e}")
    
    def _trigger_connection_callbacks(self):
        """Déclenche les callbacks de connexion"""
        for callback in self.on_connection_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Erreur callback connexion: {e}")
    
    def _get_request_id(self) -> int:
        """Génère un nouvel ID de requête"""
        self.request_id += 1
        return self.request_id
    
    @staticmethod
    def _timeframe_to_seconds(timeframe: str) -> int:
        """Convertit un timeframe en secondes"""
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400
        }
        return mapping.get(timeframe, 300)
    
    def close(self):
        """Ferme la connexion"""
        if self.ws:
            self.ws.close()
            logger.info("Connexion fermée")


class CandleBuffer:
    """Buffer pour gérer les candlesticks et détecter les nouvelles"""
    
    def __init__(self, pair: str, timeframe: str):
        self.pair = pair
        self.timeframe = timeframe
        self.candles: List[Candlestick] = []
        self.lock = Lock()
        self.callbacks: List[Callable] = []
    
    def add_candle(self, candle: Candlestick):
        """Ajoute une candlestick"""
        with self.lock:
            if not self.candles or self.candles[-1].timestamp != candle.timestamp:
                self.candles.append(candle)
                self._trigger_callbacks()
                return True
            else:
                # Mise à jour de la candelle actuelle
                self.candles[-1] = candle
                return False
    
    def _trigger_callbacks(self):
        """Déclenche les callbacks"""
        for callback in self.callbacks:
            try:
                callback(self.candles)
            except Exception as e:
                logger.error(f"Erreur callback buffer: {e}")
    
    def get_candles(self, limit: Optional[int] = None) -> List[Candlestick]:
        """Récupère les candlesticks"""
        with self.lock:
            if limit:
                return self.candles[-limit:].copy()
            return self.candles.copy()
    
    def get_last_n(self, n: int) -> List[Candlestick]:
        """Récupère les N dernières candlesticks"""
        return self.get_candles(limit=n)
