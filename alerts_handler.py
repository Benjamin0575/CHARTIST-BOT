"""
Gestionnaire des alertes Telegram
"""
import logging
from typing import Optional
import requests

from models import PatternSignal, ActiveTrade, Alert


logger = logging.getLogger(__name__)


class TelegramAlertsHandler:
    """Envoie les alertes via Telegram"""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Args:
            bot_token: Token du bot Telegram
            chat_id: ID du chat à notifier
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Tester la connexion
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Teste la connexion Telegram"""
        try:
            response = requests.get(f"{self.api_url}/getMe", timeout=5)
            if response.status_code == 200:
                logger.info("✓ Connexion Telegram établie")
                return True
        except Exception as e:
            logger.warning(f"Impossible de connecter Telegram: {e}")
        return False
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Envoie un message Telegram"""
        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json=payload,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur envoi Telegram: {e}")
            return False
    
    def handle_signal(self, signal: PatternSignal, details: dict):
        """Traite et envoie une alerte de signal"""
        try:
            message = self._format_signal_message(signal, details)
            self.send_message(message)
        except Exception as e:
            logger.error(f"Erreur traitement signal: {e}")
    
    def handle_trade(self, trade: ActiveTrade, event: str):
        """Traite et envoie une alerte de trade"""
        try:
            message = self._format_trade_message(trade, event)
            self.send_message(message)
        except Exception as e:
            logger.error(f"Erreur traitement trade: {e}")
    
    def handle_alert(self, alert: Alert):
        """Traite et envoie une alerte générale"""
        try:
            if alert.level in ["WARNING", "ERROR", "CRITICAL"]:
                message = self._format_alert_message(alert)
                self.send_message(message)
        except Exception as e:
            logger.error(f"Erreur traitement alerte: {e}")
    
    @staticmethod
    def _format_signal_message(signal: PatternSignal, details: dict) -> str:
        """Formate un message de signal"""
        return f"""
<b>🎯 Pattern Détecté</b>

<b>Type:</b> {signal.pattern_type.value.replace('_', ' ').title()}
<b>Paire:</b> {signal.pair}
<b>Timeframe:</b> {signal.timeframe}
<b>Direction:</b> {signal.direction.value.upper()}

<b>Prix Actuel:</b> {signal.entry_level:.5f}
<b>Résistance:</b> {signal.resistance_level:.5f}
<b>Support:</b> {signal.support_level:.5f}

<b>Confiance:</b> {details['final_confidence']:.0%}
<b>Multi-TF:</b> {'✓' if details.get('multi_tf_confirmed') else '✗'}
<b>Pullback:</b> {'✓' if details.get('pullback_confirmed') else '✗'}
<b>ATR:</b> {'✓' if details.get('atr_confirmed') else '✗'}
"""
    
    @staticmethod
    def _format_trade_message(trade: ActiveTrade, event: str) -> str:
        """Formate un message de trade"""
        if event == "open":
            return f"""
<b>📈 Trade Ouvert</b>

<b>ID:</b> {trade.id}
<b>Paire:</b> {trade.pair}
<b>Direction:</b> {trade.direction.value.upper()}
<b>Timeframe:</b> {trade.timeframe}

<b>Entry:</b> {trade.entry_price:.5f}
<b>Stop Loss:</b> {trade.stop_loss:.5f}
<b>Take Profit:</b> {trade.take_profit:.5f}

<b>Position Size:</b> {trade.position_size:.2f}
"""
        else:  # close
            return f"""
<b>📊 Trade Fermé</b>

<b>ID:</b> {trade.id}
<b>Paire:</b> {trade.pair}
<b>Raison:</b> {trade.exit_reason}

<b>Temps:</b> {(trade.exit_time - trade.entry_time).total_seconds():.0f}s

<b>PnL:</b> {trade.pnl:.2f} ({trade.pnl_percent:+.2f}%)

<b>{'✅ WIN' if trade.pnl > 0 else '❌ LOSS'}</b>
"""
    
    @staticmethod
    def _format_alert_message(alert: Alert) -> str:
        """Formate un message d'alerte"""
        emoji_map = {
            "WARNING": "⚠️",
            "ERROR": "❌",
            "CRITICAL": "🚨",
            "INFO": "ℹ️"
        }
        
        emoji = emoji_map.get(alert.level, "📌")
        pair_str = f" [{alert.pair}]" if alert.pair else ""
        
        return f"{emoji} <b>{alert.level}</b>{pair_str}\n\n{alert.message}"


class WebhookAlertsHandler:
    """Envoie les alertes via webhook (pour intégrations custom)"""
    
    def __init__(self, webhook_url: str):
        """
        Args:
            webhook_url: URL du webhook
        """
        self.webhook_url = webhook_url
    
    def send_event(self, event_type: str, data: dict) -> bool:
        """Envoie un événement au webhook"""
        try:
            payload = {
                'event': event_type,
                'timestamp': data.get('timestamp'),
                'data': data
            }
            
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code in [200, 201]
            
        except Exception as e:
            logger.error(f"Erreur webhook: {e}")
            return False
