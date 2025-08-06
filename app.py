# app.py (FINAL CORRECTED VERSION)
import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
from queue import Queue
import time
import telebot

# Your existing services and config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Global queue so all parts of the app can access it
task_queue = Queue()

# Global services that the worker will use
amazon_processor = None
channel_poster = None
error_notifier = None

def create_app():
    app = Flask(__name__)
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    # Use the 'global' keyword to modify the global service variables
    global amazon_processor, channel_poster, error_notifier
    
    try:
        amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
        channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
        error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

    # API Endpoint
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        task_queue.put(data)
        logger.info(f"✅ Request for URL {data.get('url')} added to queue. Queue size: {task_queue.qsize()}")
        return jsonify({'status': 'success', 'message': 'Request queued for processing.'}), 202

    # Webhook and other routes
    @app.route("/")
    def webhook():
        bot.remove_webhook()
        url = f'https://main-logic-bot-ditc.onrender.com/{Config.TELEGRAM_BOT_TOKEN}' 
        bot.set_webhook(url=url)
        return "<h1>✅ Bot is live and webhook is set!</h1>", 200
        
    # (You can add your other routes like /start, /health here if you want)

    return app

# --- Worker Logic (This is outside the factory) ---
async def process_and_post_task(payload, url):
    try:
        product_info = await amazon_processor.process_link_with_retry(url)
        if not product_info:
            await error_notifier.notify(f"❌ Failed to extract product information for {url}")
            return
        product_info['original_text'] = payload.get('original_text', '')
        product_info['images'] = payload.get('images', [])
        posting_result = channel_poster.post_to_channels(product_info)
        if not posting_result or not posting_result.get('success'):
            await error_notifier.notify(f"❌ Failed to post to channels for {url}: {posting_result.get('errors', 'Unknown error')}")
        else:
            await error_notifier.notify(f"✅ New link processed and posted successfully for URL: {url}")
    except Exception as e:
        await error_notifier.notify(f"❌ Unexpected error in background task for {url}: {e}", traceback_info=traceback.format_exc())

def queue_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("🚀 Queue worker started. Waiting for tasks...")
    while True:
        try:
            payload = task_queue.get()
            url = payload.get('url')
            logger.info(f"👷 Worker picked up task for URL: {url}")
            loop.run_until_complete(process_and_post_task(payload, url))
            task_queue.task_done()
            logger.info("🕒 Worker resting for 3 seconds to avoid rate limits.")
            time.sleep(3)
        except Exception as e:
            logger.error(f"❌ Error in queue_worker: {e}", exc_info=True)

# --- App and Thread Initialization (This is outside the factory) ---

# This creates the Flask app instance that Gunicorn will look for
app = create_app()

# This starts the background worker thread
worker_thread = threading.Thread(target=queue_worker, daemon=True)
worker_thread.start()
logger.info("✅ Queue worker thread initiated globally.")
