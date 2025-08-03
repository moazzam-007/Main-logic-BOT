import logging
import asyncio
import threading
import re  # ← MISSING IMPORT
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class ChannelPoster:
    def __init__(self, bot_token, channel_ids):
        self.bot_token = bot_token
        self.channel_ids = channel_ids if isinstance(channel_ids, list) else [channel_ids]
        logger.info(f"📢 ChannelPoster initialized with {len(self.channel_ids)} channels")

    def post_to_channels(self, product_info, images=None):
        """Post product info to all configured channels - THREAD SAFE"""
        posted_channels = []
        errors = []
        
        try:
            # Run in separate thread to avoid event loop conflicts
            result = self._run_in_thread(self._async_post_to_channels, product_info, images)
            posted_channels = result.get('posted_channels', [])
            errors = result.get('errors', [])
                
        except Exception as e:
            logger.error(f"❌ Error in posting coordination: {e}")
            errors.append(str(e))
        
        return {
            'success': len(posted_channels) > 0,
            'posted_channels': posted_channels,
            'errors': errors
        }

    def _run_in_thread(self, async_func, *args):
        """Run async function in separate thread"""
        result = {}
        
        def thread_target():
            try:
                # Create fresh event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result['data'] = loop.run_until_complete(async_func(*args))
                finally:
                    loop.close()
            except Exception as e:
                result['error'] = str(e)
                logger.error(f"❌ Thread error: {e}")
        
        thread = threading.Thread(target=thread_target)
        thread.start()
        thread.join(timeout=30)  # 30 second timeout
        
        if 'error' in result:
            raise Exception(result['error'])
        
        return result.get('data', {'posted_channels': [], 'errors': ['Thread timeout']})

    async def _async_post_to_channels(self, product_info, images=None):
        """Async method to post to all channels"""
        posted_channels = []
        errors = []
        
        # Create fresh bot instance for this async context
        bot = Bot(token=self.bot_token)
        
        for channel_id in self.channel_ids:
            try:
                await self._post_to_single_channel(bot, channel_id, product_info, images)
                posted_channels.append(channel_id)
                logger.info(f"✅ Posted to channel: {channel_id}")
                
                # Small delay between posts
                await asyncio.sleep(0.5)
                
            except Exception as e:
                error_msg = f"Failed to post to {channel_id}: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)
        
        return {
            'posted_channels': posted_channels,
            'errors': errors
        }

    async def _post_to_single_channel(self, bot, channel_id, product_info, images=None):
        """Post to a single channel with clean format"""
        try:
            # Get product details
            title = product_info.get('title', '').strip()
            price = product_info.get('price', 'Price not available')
            short_link = product_info.get('short_link')  # TinyURL
            affiliate_link = product_info.get('affiliate_link', '')
            original_text = product_info.get('original_text', '').strip()
            
            # USE TINY URL as primary link
            link_to_display = short_link if short_link else affiliate_link
            
            # Create CLEAN message format
            if title and len(title) > 5:
                # Use extracted title
                message_text = f"🛒 **{title}**\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
            else:
                # Extract title from original text if available
                if original_text and len(original_text) > 10:
                    # Clean original text (remove extra links and emojis)
                    clean_lines = []
                    for line in original_text.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('http') and not line.startswith('👉') and not line.startswith('*'):
                            # Remove excessive emojis and clean
                            clean_line = re.sub(r'[📱💰🎉🔥⭐️✨🛒👉💸🎁🚀]', '', line).strip()
                            if clean_line and len(clean_line) > 5:
                                clean_lines.append(clean_line)
                                break
                    
                    if clean_lines:
                        title_from_text = clean_lines[0][:60] + ("..." if len(clean_lines[0]) > 60 else "")
                        message_text = f"🛒 **{title_from_text}**\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
                    else:
                        message_text = f"🔗 **Amazon Deal**\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
                else:
                    message_text = f"🔗 **Amazon Deal**\n💰 **Price:** {price}\n\n🔗 **Link:** {link_to_display}\n\n📝 **Note:** Copy link and always open in browser"
            
            # Check if we have images
            if images and len(images) > 0:
                # Send image with caption (single message)
                image_file_id = images[0].get('file_id')  # Use first image
                if image_file_id:
                    await bot.send_photo(
                        chat_id=channel_id,
                        photo=image_file_id,
                        caption=message_text,
                        parse_mode='Markdown'
                    )
                else:
                    # No valid image, send text only
                    await bot.send_message(
                        chat_id=channel_id,
                        text=message_text,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
            else:
                # No images, send text only
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

    def test_connection(self):
        """Test bot connection"""
        try:
            result = self._run_in_thread(self._async_test_connection)
            return result.get('success', False)
        except Exception as e:
            logger.error(f"❌ Bot connection test failed: {e}")
            return False

    async def _async_test_connection(self):
        """Async bot connection test"""
        try:
            bot = Bot(token=self.bot_token)
            bot_info = await bot.get_me()
            logger.info(f"✅ Bot connection successful: @{bot_info.username}")
            return {'success': True}
        except Exception as e:
            logger.error(f"❌ Bot connection failed: {e}")
            return {'success': False}
