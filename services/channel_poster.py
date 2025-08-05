# services/channel_poster.py (FINAL VERSION)
import logging
import time

logger = logging.getLogger(__name__)

class ChannelPoster:
    def __init__(self, bot, channel_ids):
        self.bot = bot
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
        """Post to a single channel with smart image and clean format"""
        # Sab data nikal lein
        scraped_title = product_info.get('title', '').strip()
        price = product_info.get('price', 'Price not available')
        link_to_display = product_info.get('short_link') or product_info.get('affiliate_link', '')
        original_text = product_info.get('original_text', '').strip()
        
        # Image ki logic: pehle monitor bot wali, phir scraped
        images = product_info.get('images', [])
        image_file_id = images[0].get('file_id') if images else None
        scraped_image_url = product_info.get('image_url')
        final_image = image_file_id or scraped_image_url

        # Title ki logic: pehle scraped, phir original text
        final_title = scraped_title
        if not final_title:
            # URL ko original text se hata dein taake saaf title mile
            clean_original_text = original_text.split('http')[0].strip()
            if clean_original_text:
                final_title = clean_original_text
            else:
                final_title = "Amazon Deal" # Aakhri fallback

        # Message banayein
        message_text = f"🛒 *{final_title}*\n\n"
        
        # Price ki line sirf tab add karein jab price mili ho
        if price and price != 'Price not available':
            message_text += f"💰 *Price:* {price}\n\n"
            
        message_text += f"🔗 *Link:* {link_to_display}\n\n"
        message_text += "📝 *Note:* Copy link and always open in browser"
        
        # Post karein
        try:
            if final_image:
                self.bot.send_photo(
                    chat_id=channel_id,
                    photo=final_image,
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
            raise
