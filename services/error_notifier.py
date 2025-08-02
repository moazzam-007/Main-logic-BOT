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
            
            # Format original text first
            formatted_text = original_text[:200] + '...' if len(original_text) > 200 else original_text
            
            notification_message = f"""🚨 **Enhanced Affiliate Bot Error**

⏰ **Time:** {timestamp}
🔗 **URL:** `{url}`
❌ **Error:** {error_message}

📝 **Original Text:** 
{formatted_text}

🔧 **Action Required:** Please check the logs and resolve the issue."""
            
            return self._send_notification(notification_message)
            
        except Exception as e:
            logger.error(f"Error sending error notification: {e}")
            return False
    
    def notify_startup(self):
        """Send startup notification"""
        if not self.enabled:
            return False
        
        try:
            message = f"""🚀 **Enhanced Affiliate Bot Started**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
✅ **Status:** Bot is running and ready to process links
🔧 **Services:** All services initialized successfully"""
            
            return self._send_notification(message)
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False
    
    def notify_channel_failure(self, channel_id, error_message):
        """Notify about channel posting failures"""
        if not self.enabled:
            return False
        
        try:
            message = f"""📺 **Channel Posting Error**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📺 **Channel ID:** `{channel_id}`
❌ **Error:** {error_message}

🔧 **Suggestion:** Check channel permissions and bot access."""
            
            return self._send_notification(message)
            
        except Exception as e:
            logger.error(f"Error sending channel failure notification: {e}")
            return False
    
    def notify_duplicate_detection_cleanup(self, cleaned_count):
        """Notify about duplicate detection cleanup"""
        if not self.enabled or cleaned_count == 0:
            return False
        
        try:
            message = f"""🧹 **Duplicate Detection Cleanup**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
📊 **Cleaned Entries:** {cleaned_count}
✅ **Status:** Memory cleanup completed successfully"""
            
            return self._send_notification(message)
            
        except Exception as e:
            logger.error(f"Error sending cleanup notification: {e}")
            return False
    
    def _send_notification(self, message):
        """Send notification message to Telegram"""
        try:
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': self.error_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=15)
            response.raise_for_status()
            
            if response.status_code == 200:
                logger.info("✅ Error notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send notification: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    def test_notification(self):
        """Send test notification"""
        if not self.enabled:
            logger.warning("Error notifications are disabled")
            return False
        
        test_message = f"""🧪 **Test Notification**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
✅ **Status:** Error notification system is working properly
🤖 **Bot:** Enhanced Affiliate Bot"""
        
        return self._send_notification(test_message)
