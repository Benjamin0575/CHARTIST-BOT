#!/usr/bin/env python3
"""
CHARTIST-BOT - Bot de Trading Automatisé basé sur Figures Chartistes
Point d'entrée principal
"""
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

import dotenv

from bot_engine import ChartistBotEngine
from alerts_handler import TelegramAlertsHandler


# Configuration du logging
def setup_logging():
    """Configure le système de logging"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"chartist_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> dict:
    """Charge la configuration"""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Erreur: Fichier {config_path} non trouvé")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Erreur: {config_path} n'est pas un JSON valide")
        sys.exit(1)


def load_env_vars():
    """Charge les variables d'environnement"""
    dotenv.load_dotenv()
    
    # Vérifier les variables critiques
    required_vars = [
        'DERIV_APP_ID',
        'DERIV_API_TOKEN',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"⚠️  Variables d'environnement manquantes: {', '.join(missing)}")
        print("Ces variables doivent être définies dans un fichier .env ou les variables système")
        print("\nExemple .env:")
        print("DERIV_APP_ID=your_app_id")
        print("DERIV_API_TOKEN=your_api_token")
        print("TELEGRAM_BOT_TOKEN=your_bot_token")
        print("TELEGRAM_CHAT_ID=your_chat_id")
        return False
    
    return True


def inject_env_into_config(config: dict) -> dict:
    """Injecte les variables d'environnement dans la config"""
    # Deriv
    config['deriv']['app_id'] = os.getenv('DERIV_APP_ID', config['deriv'].get('app_id'))
    config['deriv']['api_token'] = os.getenv('DERIV_API_TOKEN', config['deriv'].get('api_token'))
    
    # Telegram
    config['alerts']['telegram_bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN', 
                                                       config['alerts'].get('telegram_bot_token'))
    config['alerts']['telegram_chat_id'] = os.getenv('TELEGRAM_CHAT_ID',
                                                      config['alerts'].get('telegram_chat_id'))
    
    return config


def main():
    """Fonction principale"""
    
    logger = setup_logging()
    
    logger.info("=" * 60)
    logger.info("CHARTIST-BOT - Bot de Trading Automatisé")
    logger.info("=" * 60)
    
    # Charger configuration
    logger.info("Chargement de la configuration...")
    config = load_config()
    
    # Charger variables d'environnement
    if not load_env_vars():
        logger.error("Variables d'environnement insuffisantes")
        return False
    
    config = inject_env_into_config(config)
    logger.info("✓ Configuration chargée")
    
    # Créer et initialiser le bot
    logger.info("Initialisation du bot...")
    bot = ChartistBotEngine(config)
    
    if not bot.initialize():
        logger.error("Erreur initialisation du bot")
        return False
    
    # Initialiser les alertes Telegram
    if config['alerts'].get('telegram_enabled'):
        logger.info("Initialisation des alertes Telegram...")
        telegram_handler = TelegramAlertsHandler(
            bot_token=config['alerts']['telegram_bot_token'],
            chat_id=config['alerts']['telegram_chat_id']
        )
        
        # Attacher les callbacks
        bot.add_callback(telegram_handler.handle_signal, "signal")
        bot.add_callback(telegram_handler.handle_trade, "trade")
        bot.add_callback(telegram_handler.handle_alert, "alert")
        
        logger.info("✓ Alertes Telegram initialisées")
    
    # Démarrer le bot
    logger.info("Démarrage du bot...")
    try:
        bot.start()
    except KeyboardInterrupt:
        logger.info("Arrêt du bot (Ctrl+C)")
        bot.stop()
        return True
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
