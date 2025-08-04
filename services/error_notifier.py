import aiohttp
import logging
import asyncio
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class ErrorNotifier:
    def __init__(self, bot_token, error_chat_id):
        self.bot_token = bot_token
        self.error_chat_id = error_chat_id
        self.telegram_api_url = f"https://api.telegram.org/bot{bot_token}"
        self.enabled = bool(bot_token and error_chat_id)
        
        if not self.enabled:
            logger.warning("⚠️ Error notifications disabled - missing bot token or error chat ID")
            
    async def notify(self, message, traceback_info=None):
        """Send a general notification to the configured chat"""
        if not self.enabled:
            return False
            
        full_message = f"{message}"
        if traceback_info:
            full_message += f"\n\n```python\n{traceback_info}\n```"

        try:
            return await self._send_notification(full_message)
        except Exception as e:
            logger.error(f"Error sending general notification: {e}")
            return False

    async def notify_error(self, url, error_message, original_text="", traceback_info=None):
        """Send error notification to configured chat"""
        if not self.enabled:
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            formatted_text = original_text[:200] + '...' if len(original_text) > 200 else original_text
            
            notification_message = f"""🚨 **Enhanced Affiliate Bot Error**

⏰ **Time:** {timestamp}
🔗 **URL:** `{url}`
❌ **Error:** {error_message}

📝 **Original Text:**
{formatted_text}"""

            if traceback_info:
                notification_message += f"\n\n```python\n{traceback_info}\n```"
                
            return await self._send_notification(notification_message)
            
        except Exception as e:
            logger.error(f"Error sending specific error notification: {e}")
            return False
    
    async def notify_startup(self):
        """Send startup notification"""
        if not self.enabled:
            return False
        
        try:
            message = f"""🚀 **Enhanced Affiliate Bot Started**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
✅ **Status:** Bot is running and ready to process links"""
            
            return await self._send_notification(message)
            
        except Exception as e:
            logger.error(f"Error sending startup notification: {e}")
            return False
            
    async def _send_notification(self, message):
        """Send notification message to Telegram"""
        try:
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': self.error_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, timeout=15) as response:
                    response.raise_for_status()
                    
                    if response.status == 200:
                        logger.info("✅ Error notification sent successfully")
                        return True
                    else:
                        logger.error(f"Failed to send notification: {response.status}")
                        return False
            
        except (aiohttp.ClientError, asyncio.TimeoutError, Exception) as e:
            logger.error(f"Error sending notification: {e}")
            return False

    async def test_notification(self):
        """Send test notification"""
        if not self.enabled:
            logger.warning("Error notifications are disabled")
            return False
        
        test_message = f"""🧪 **Test Notification**

⏰ **Time:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
✅ **Status:** Error notification system is working properly
🤖 **Bot:** Enhanced Affiliate Bot"""
        
        return await self._send_notification(test_message)
