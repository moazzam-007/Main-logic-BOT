import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorNotifier:
    def __init__(self, bot_token, error_chat_id):
        self.bot_token = bot_token
        self.error_chat_id = error_chat_id
        self.telegram_api_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and error_chat_id)
        
        if not self.enabled:
            logger.warning("⚠️ Error notifications disabled - missing bot token or error chat ID")
    
    def notify_error(self, url, error_message, original_text=""):
        """Send error notification to configured chat"""
        if not self.enabled:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            notification_message = f"""
🚨 **Enhanced Affiliate Bot Error**

⏰ **Time:** {timestamp}
🔗 **URL:** `{url}`
❌ **Error:** {error_message}

📝 **Original Text:**
