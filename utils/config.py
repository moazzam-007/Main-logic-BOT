import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        # Bot configuration
        self.BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'budgetlooks08-21')
        
        # Channel configuration - support multiple channels
        channel_ids_str = os.getenv('OUTPUT_CHANNELS', '-1002763897032')
        self.CHANNEL_IDS = [
            int(channel_id.strip()) 
            for channel_id in channel_ids_str.split(',') 
            if channel_id.strip()
        ] if channel_ids_str else []
        
        # Error notification chat
        self.ERROR_CHAT_ID = os.getenv('ERROR_CHAT_ID')
        
        # TinyURL API (if needed)
        self.TINYURL_API_TOKEN = os.getenv('TINYURL_API_TOKEN')
        
        # Duplicate detection settings
        self.DUPLICATE_DETECTION_HOURS = int(os.getenv('DUPLICATE_DETECTION_HOURS', '24'))
        
        self._validate_config()
    
    def _validate_config(self):
        """Validate essential configuration"""
        if not self.BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set")
            
        if not self.CHANNEL_IDS:
            logger.warning("⚠️ No CHANNEL_IDS configured")
            
        if not self.AFFILIATE_TAG:
            logger.warning("⚠️ No AFFILIATE_TAG set, using default")
            
        logger.info(f"✅ Configuration loaded - {len(self.CHANNEL_IDS)} channels configured")

    # Class-level properties for backward compatibility
    @property
    def TELEGRAM_BOT_TOKEN(self):
        return self.BOT_TOKEN
    
    @property
    def OUTPUT_CHANNELS(self):
        return self.CHANNEL_IDS

# Create instance for use
Config = Config()
