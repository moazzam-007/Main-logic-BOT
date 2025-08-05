# services/channel_poster.py (FINAL-FINAL VERSION)
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
                time.sleep(1)
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
        scraped_title = product_info.get('title', '').strip()
        price = product_info.get('price', 'Price not available')
        link_to_display = product_info.get('short_link') or product_info.get('affiliate_link', '')
        original_text = product_info.get('original_text', '').strip()
        
        # === YEH LOGIC BADLI GAYI HAI ===
        # Hum ab monitor-bot se aane wali file_id ko ignore karenge
        # aur hamesha scraped URL hi istemal karenge.
        final_image = product_info.get('image_url')
        # =================================

        final_title = scraped_title
        if not final_title:
            clean_original_text = original_text.split('http')[0].strip()
            if clean_original_text:
                final_title = clean_original_text
            else:
                final_title = "Amazon Deal"

        message_text = f"🛒 *{final_title}*\n\n"
        
        if price and price != 'Price not available':
            message_text += f"💰 *Price:* {price}\n\n"
            
        message_text += f"🔗 *Link:* {link_to_display}\n\n"
        message_text += "📝 *Note:* Copy link and always open in browser"
        
        try:
            if final_image:
                self.bot.send_photo(
                    chat_id=channel_id,
                    photo=final_image,  # Yeh ab hamesha ek URL hoga
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
