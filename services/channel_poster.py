import logging
import asyncio
from telegram import Bot, InputMediaPhoto
from telegram.error import TelegramError
from functools import wraps

logger = logging.getLogger(__name__)

# Retry decorator for async functions
def retry_on_failure(max_retries=3, delay=5):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.warning(f"❌ Attempt {attempt + 1} failed with error: {e}. Retrying in {delay}s...")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(delay)
            return None
        return wrapper
    return decorator

class ChannelPoster:
    def __init__(self, bot_token, channel_ids):
        self.bot = Bot(bot_token)
        self.channel_ids = channel_ids if isinstance(channel_ids, list) else [channel_ids]
        logger.info(f"📢 ChannelPoster initialized with {len(self.channel_ids)} channels")

    @retry_on_failure(max_retries=2, delay=3)
    async def post_to_channels_with_retry(self, product_info):
        """Post product info to all configured channels with retries"""
        posted_channels = []
        errors = []
        
        for channel_id in self.channel_ids:
            try:
                await self._post_to_single_channel(self.bot, channel_id, product_info)
                posted_channels.append(channel_id)
                logger.info(f"✅ Posted to channel: {channel_id}")
                
                # Small async delay between posts
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = f"Failed to post to {channel_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            'success': len(posted_channels) > 0,
            'posted_channels': posted_channels,
            'errors': errors
        }

    async def _post_to_single_channel(self, bot, channel_id, product_info):
        """Post to a single channel with smart image and clean format"""
        title = product_info.get('title', '').strip()
        price = product_info.get('price', 'Price not available')
        short_link = product_info.get('short_link')
        affiliate_link = product_info.get('affiliate_link', '')
        original_text = product_info.get('original_text', '').strip()
        images = product_info.get('images', [])
        image_url = product_info.get('image_url')
        
        final_image = None
        if images and images[0].get('file_id'):
            final_image = images[0].get('file_id')
        elif image_url:
            final_image = image_url
        
        link_to_display = short_link if short_link else affiliate_link
        
        message_text = f"🛒 **{title or 'Amazon Deal'}**\n\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"

        try:
            if final_image:
                await bot.send_photo(
                    chat_id=channel_id,
                    photo=final_image,
                    caption=message_text,
                    parse_mode='Markdown'
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    text=message_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
            
        except TelegramError as e:
            logger.error(f"❌ Telegram error posting to {channel_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ General error posting to {channel_id}: {e}")
            raise
