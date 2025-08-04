import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    # Bot configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'budgetlooks08-21')
    
    # Output Channel configuration
    output_channels_str = os.getenv('OUTPUT_CHANNELS', '')
    OUTPUT_CHANNELS = [
        int(channel_id.strip())
        for channel_id in output_channels_str.split(',')
        if channel_id.strip()
    ] if output_channels_str else []
    
    # Error notification chat
    ERROR_CHAT_ID = os.getenv('ERROR_CHAT_ID')
    
    # TinyURL API (if needed)
    TINYURL_API_TOKEN = os.getenv('TINYURL_API_TOKEN')
    
    _validate_config()

    @staticmethod
    def _validate_config():
        """Validate essential configuration"""
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
            raise ValueError("TELEGRAM_BOT_TOKEN not set")
        
        if not Config.OUTPUT_CHANNELS:
            logger.warning("⚠️ No OUTPUT_CHANNELS configured")
        
        if not Config.AFFILIATE_TAG:
            logger.warning("⚠️ No AFFILIATE_TAG set, using default")

# Ensure config is validated at startup
try:
    Config._validate_config()
except ValueError:
    pass
