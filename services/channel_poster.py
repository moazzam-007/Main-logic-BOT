import logging
import asyncio
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class ChannelPoster:
    def __init__(self, bot_token, channel_ids):
        self.bot = Bot(token=bot_token)
        self.channel_ids = channel_ids if isinstance(channel_ids, list) else [channel_ids]
        logger.info(f"📢 ChannelPoster initialized with {len(self.channel_ids)} channels")

    def post_to_channels(self, product_info, images=None):
        """Post product info to all configured channels with proper formatting"""
        posted_channels = []
        errors = []
        
        try:
            # Run async posting in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._async_post_to_channels(product_info, images))
                posted_channels = result.get('posted_channels', [])
                errors = result.get('errors', [])
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"❌ Error in posting coordination: {e}")
            errors.append(str(e))
        
        return {
            'success': len(posted_channels) > 0,
            'posted_channels': posted_channels,
            'errors': errors
        }

    async def _async_post_to_channels(self, product_info, images=None):
        """Async method to post to all channels"""
        posted_channels = []
        errors = []
        
        for channel_id in self.channel_ids:
            try:
                await self._post_to_single_channel(channel_id, product_info, images)
                posted_channels.append(channel_id)
                logger.info(f"✅ Posted to channel: {channel_id}")
                
            except Exception as e:
                error_msg = f"Failed to post to {channel_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            'posted_channels': posted_channels,
            'errors': errors
        }

    async def _post_to_single_channel(self, channel_id, product_info, images=None):
        """Post to a single channel with clean format"""
        try:
            # Get product details
            title = product_info.get('title', 'Amazon Product')
            price = product_info.get('price', 'Price not available')
            short_link = product_info.get('short_link')  # TinyURL
            affiliate_link = product_info.get('affiliate_link', '')
            original_text = product_info.get('original_text', '')
            
            # USE TINY URL as primary link
            link_to_display = short_link if short_link else affiliate_link
            
            # Create CLEAN message format
            if title and title != 'Amazon Product':
                # Use extracted title
                message_text = f"🛒 **{title}**\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
            else:
                # Extract title from original text if available
                if original_text and len(original_text) > 10:
                    # Clean original text (remove extra links)
                    clean_text = original_text.split('http')[0].strip()
                    if clean_text:
                        message_text = f"🛒 **{clean_text}**\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
                    else:
                        message_text = f"🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
                else:
                    message_text = f"🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
            
            # Check if we have images
            if images and len(images) > 0:
                # Send image with caption (single message)
                image_file_id = images[0].get('file_id')  # Use first image
                if image_file_id:
                    await self.bot.send_photo(
                        chat_id=channel_id,
                        photo=image_file_id,
                        caption=message_text,
                        parse_mode='Markdown'
                    )
                else:
                    # No valid image, send text only
                    await self.bot.send_message(
                        chat_id=channel_id,
                        text=message_text,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
            else:
                # No images, send text only
                await self.bot.send_message(
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

    def test_connection(self):
        """Test bot connection"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                bot_info = loop.run_until_complete(self.bot.get_me())
                logger.info(f"✅ Bot connection successful: @{bot_info.username}")
                return True
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"❌ Bot connection failed: {e}")
            return False
