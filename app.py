import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
import telebot
from concurrent.futures import ThreadPoolExecutor # Naya import
import time

# Services aur Config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === NAYA THREAD POOL EXECUTOR ===
# Yeh ek fixed worker team banayega (e.g., 3 workers)
executor = ThreadPoolExecutor(max_workers=3)

# Global services for worker
amazon_processor = None
channel_poster = None
error_notifier = None

def create_app():
    app = Flask(__name__)
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    def initialize_services():
        """Services ko retry logic ke saath initialize karein"""
        global amazon_processor, channel_poster, error_notifier
        for attempt in range(3):
            try:
                amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
                channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
                error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
                logger.info("✅ All services initialized successfully")
                return True
            except Exception as e:
                logger.warning(f"⚠️ Service initialization failed (Attempt {attempt + 1}): {e}")
                time.sleep(5)
        logger.error("❌ Service initialization failed after all retries.")
        return False

    if not initialize_services():
        # Agar services start na hon, to app crash kar dein
        raise RuntimeError("Could not initialize critical services.")

    # Background task ki logic
    async def process_and_post_task(payload, url):
        try:
            product_info = await amazon_processor.process_link_with_retry(url)
            if not product_info:
                await error_notifier.notify(f"❌ Failed to extract product info for {url}")
                return
            product_info['original_text'] = payload.get('original_text', '')
            product_info['images'] = payload.get('images', [])
            posting_result = channel_poster.post_to_channels(product_info)
            if not posting_result or not posting_result.get('success'):
                await error_notifier.notify(f"❌ Failed to post to channels for {url}: {posting_result.get('errors', 'Unknown error')}")
            else:
                await error_notifier.notify(f"✅ Successfully posted: {url}")
        except Exception as e:
            await error_notifier.notify(f"❌ Unexpected error in task for {url}: {e}", traceback_info=traceback.format_exc())

    def sync_task_wrapper(payload):
        """Async task ko executor ke thread mein chalane ke liye sync wrapper"""
        url = payload.get('url')
        logger.info(f"👷 Worker picked up task for URL: {url}")
        try:
            asyncio.run(process_and_post_task(payload, url))
            logger.info(f"✅ Task completed for URL: {url}")
        except Exception as e:
            logger.error(f"❌ Error in sync_task_wrapper for {url}: {e}", exc_info=True)

    # API Endpoint
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        try:
            data = request.get_json(force=True)
            if not data or not data.get('url'):
                return jsonify({'status': 'error', 'message': 'URL is required'}), 400
            
            # Task ko ThreadPoolExecutor ko submit karein
            executor.submit(sync_task_wrapper, data)
            
            logger.info(f"✅ Request for URL {data.get('url')} submitted to executor.")
            return jsonify({'status': 'success', 'message': 'Request queued for processing.'}), 202
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # Secure Webhook Route
    @app.route('/' + Config.TELEGRAM_BOT_TOKEN, methods=['POST'])
    def telegram_webhook():
        # Secret token se request ko verify karein
        if request.headers.get('X-Telegram-Bot-Api-Secret-Token') == Config.TELEGRAM_SECRET_TOKEN:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "!", 200
        else:
            return "Forbidden", 403

    # Status Page
    @app.route("/")
    def index():
        return "<h1>🤖 Logic Bot is running!</h1>"

    # Webhook set karne ke liye alag se function
    def setup_webhook():
        logger.info("Setting up webhook...")
        bot.remove_webhook()
        # Ab humara webhook URL secure hai
        webhook_url = f"{Config.WEBHOOK_URL}/{Config.TELEGRAM_BOT_TOKEN}"
        bot.set_webhook(url=webhook_url, secret_token=Config.TELEGRAM_SECRET_TOKEN)
        logger.info("✅ Webhook set successfully!")

    # App start hone par ek baar webhook set karein
    with app.app_context():
        setup_webhook()

    return app
