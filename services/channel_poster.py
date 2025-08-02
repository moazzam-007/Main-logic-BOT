import requests
import logging
from utils.helpers import format_channel_message

logger = logging.getLogger(__name__)

class ChannelPoster:
    def __init__(self, bot_token, channel_ids):
        self.bot_token = bot_token
        self.channel_ids = channel_ids if isinstance(channel_ids, list) else []
        self.telegram_api_url = f"https://api.telegram.org/bot{bot_token}"
        
    def post_to_channels(self, product_info):
        """Post product info to all configured channels"""
        if not self.channel_ids:
            logger.error("❌ No channels configured for posting")
            return {"success": False, "error": "No channels configured"}
        
        posted_channels = []
        failed_channels = []
        
        for channel_id in self.channel_ids:
            try:
                success = self._post_to_single_channel(channel_id, product_info)
                if success:
                    posted_channels.append(channel_id)
                    logger.info(f"✅ Posted to channel: {channel_id}")
                else:
                    failed_channels.append(channel_id)
                    logger.error(f"❌ Failed to post to channel: {channel_id}")
            except Exception as e:
                logger.error(f"❌ Error posting to channel {channel_id}: {str(e)}")
                failed_channels.append(channel_id)
        
        if posted_channels:
            return {
                "success": True,
                "posted_channels": posted_channels,
                "failed_channels": failed_channels
            }
        else:
            return {
                "success": False,
                "error": "Failed to post to any channel",
                "failed_channels": failed_channels
            }
    
    def _post_to_single_channel(self, channel_id, product_info):
        """Post to a single channel"""
        try:
            # Format message
            message_text = format_channel_message(product_info)
            
            # Check if we have image
            if product_info.get('image_file_id'):
                # Use existing image file ID
                return self._send_photo_with_file_id(
                    channel_id, 
                    product_info['image_file_id'], 
                    message_text
                )
            elif product_info.get('image_url'):
                # Use scraped image URL
                return self._send_photo_with_url(
                    channel_id, 
                    product_info['image_url'], 
                    message_text
                )
            else:
                # Text only message
                return self._send_text_message(channel_id, message_text)
                
        except Exception as e:
            logger.error(f"Error posting to channel {channel_id}: {str(e)}")
            return False
    
    def _send_photo_with_file_id(self, chat_id, file_id, caption):
        """Send photo using Telegram file ID"""
        try:
            url = f"{self.telegram_api_url}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'photo': file_id,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending photo with file ID to {chat_id}: {e}")
            return False
    
    def _send_photo_with_url(self, chat_id, photo_url, caption):
        """Send photo using image URL"""
        try:
            url = f"{self.telegram_api_url}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'photo': photo_url,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=30)
            response.raise_for_status()
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending photo with URL to {chat_id}: {e}")
            # Fallback to text message
            return self._send_text_message(chat_id, caption)
    
    def _send_text_message(self, chat_id, text):
        """Send text message"""
        try:
            url = f"{self.telegram_api_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=data, timeout=15)
            response.raise_for_status()
            return response.status_code == 200
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending text message to {chat_id}: {e}")
            return False
    
    def test_channel_connection(self, channel_id):
        """Test connection to a specific channel"""
        try:
            test_message = "🤖 Test message from Enhanced Affiliate Bot"
            return self._send_text_message(channel_id, test_message)
        except Exception as e:
            logger.error(f"Channel connection test failed for {channel_id}: {e}")
            return False
