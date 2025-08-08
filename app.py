# app.py (FINAL-FINAL VERSION WITH DUPLICATE DETECTION)
import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
import telebot
from threading import Lock
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config
from services.duplicate_detector import DuplicateDetector # Naya import

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

processing_lock = Lock()
# Duplicate detector ko global banayein
duplicate_detector = DuplicateDetector(detection_hours=48)

def create_app():
    app = Flask(__name__)
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    # Services ko global scope mein initialize karein taake worker unhe use kar sake
    global amazon_processor, channel_poster, error_notifier
    amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
    channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
    error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
    logger.info("✅ All services initialized successfully")

    async def process_and_post_task(payload, url):
        try:
            product_info = await amazon_processor.process_link_with_retry(url)
            if not product_info:
                await error_notifier.notify(f"❌ Failed to extract product info for {url}")
                return
            product_info['original_text'] = payload.get('original_text', '')
            product_info['images'] = payload.get('images', [])
            posting_result = channel_poster.post_to_channels(product_info)
            if posting_result and posting_result.get('success'):
                await error_notifier.notify(f"✅ Successfully posted: {url}")
        except Exception as e:
            await error_notifier.notify(f"❌ Unexpected error in task for {url}: {e}", traceback_info=traceback.format_exc())

    def sync_task_wrapper(payload):
        url = payload.get('url')
        clean_url = url.split('?')[0] # Basic cleaning for the check

        # Double-check for duplicate inside the lock
        if duplicate_detector.is_duplicate(clean_url):
            logger.info(f"🔄 Duplicate link confirmed by Logic Bot. Skipping: {url}")
            return

        # Mark as processed immediately after confirming it's new
        duplicate_detector.mark_as_processed(clean_url)

        logger.info(f"⏳ Waiting to acquire lock for URL: {url}")
        with processing_lock:
            logger.info(f"✅ Lock acquired. Processing URL: {url}")
            try:
                asyncio.run(process_and_post_task(payload, url))
            except Exception as e:
                logger.error(f"❌ Error in sync_task_wrapper: {e}", exc_info=True)
        logger.info(f"✅ Lock released for URL: {url}")

    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        threading.Thread(target=sync_task_wrapper, args=(data,)).start()
        return jsonify({'status': 'success', 'message': 'Request received.'}), 202
    
    # (Baki ke sabhi routes waise hi rahenge)
    @app.route("/")
    def webhook():
        bot.remove_webhook()
        url = f'{Config.WEBHOOK_URL}/{Config.TELEGRAM_BOT_TOKEN}'
        bot.set_webhook(url=url, secret_token=Config.TELEGRAM_SECRET_TOKEN)
        return "<h1>✅ Bot is live and webhook is set!</h1>"

    return app
