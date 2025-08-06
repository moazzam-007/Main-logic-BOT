import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    # Bot configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    AFFILIATE_TAG = os.getenv('AFFILIATE_TAG', 'budgetlooks08-21')
    
    # Naye variables
    WEBHOOK_URL = os.getenv('WEBHOOK_URL') # Aapke Render app ka URL
    TELEGRAM_SECRET_TOKEN = os.getenv('TELEGRAM_SECRET_TOKEN') # Security ke liye ek secret password

    # Output Channel configuration
    output_channels_str = os.getenv('OUTPUT_CHANNELS', '')
    OUTPUT_CHANNELS = [int(ch.strip()) for ch in output_channels_str.split(',') if ch.strip()] if output_channels_str else []
    
    # Error notification chat
    ERROR_CHAT_ID = os.getenv('ERROR_CHAT_ID')
    
    # TinyURL API (if needed)
    TINYURL_API_TOKEN = os.getenv('TINYURL_API_TOKEN')

# Validation
required_vars = ["TELEGRAM_BOT_TOKEN", "WEBHOOK_URL", "OUTPUT_CHANNELS"]
missing_vars = [var for var in required_vars if not getattr(Config, var)]
if missing_vars:
    error_msg = f"❌ Missing required environment variables: {', '.join(missing_vars)}"
    logger.error(error_msg)
    raise ValueError(error_msg)

logger.info("✅ All required environment variables are set")
