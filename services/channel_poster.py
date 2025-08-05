# services/channel_poster.py (Updated Code)
import logging
import time

logger = logging.getLogger(__name__)

class ChannelPoster:
    def __init__(self, bot, channel_ids):
        self.bot = bot  # Hum telebot ka instance direct istemal karenge
        self.channel_ids = channel_ids if isinstance(channel_ids, list) else [channel_ids]
        logger.info(f"📢 ChannelPoster initialized with {len(self.channel_ids)} channels")

    def post_to_channels(self, product_info):
        """Post product info to all configured channels"""
        posted_channels = []
        errors = []
        
        for channel_id in self.channel_ids:
            try:
                self._post_to_single_channel(channel_id, product_info)
                posted_channels.append(channel_id)
                logger.info(f"✅ Posted to channel: {channel_id}")
                time.sleep(1) # Telegram API limits se bachne ke liye thora delay
            except Exception as e:
                error_msg = f"Failed to post to {channel_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            'success': len(posted_channels) > 0,
            'posted_channels': posted_channels,
            'errors': errors
        }

    def _post_to_single_channel(self, channel_id, product_info):
        """Post to a single channel"""
        title = product_info.get('title', '').strip()
        price = product_info.get('price', 'Price not available')
        link_to_display = product_info.get('short_link') or product_info.get('affiliate_link', '')
        image = product_info.get('images', [{}])[0].get('file_id') or product_info.get('image_url')

        message_text = f"🛒 *{title or 'Amazon Deal'}*\n\n💰 *Price:* {price}\n\n🔗 *Link:* {link_to_display}\n\n📝 *Note:* Copy link and always open in browser"
        
        try:
            if image:
                self.bot.send_photo(
                    chat_id=channel_id,
                    photo=image,
                    caption=message_text,
                    parse_mode='Markdown'
                )
            else:
                self.bot.send_message(
                    chat_id=channel_id,
                    text=message_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
        except Exception as e:
            logger.error(f"❌ Telegram error posting to {channel_id}: {e}")
            raise # Error ko aage bhejein taake retry ho sake
