import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
from queue import Queue
import time
import telebot # Hum telebot hi istemal karenge

# Aapke existing services aur config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Aapka banaya hua Queue (Yeh bohot acha hai!)
task_queue = Queue()

def create_app():
    app = Flask(__name__)
    # Humara telebot instance
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    try:
        amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
        # Humara corrected channel_poster initialization
        channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
        error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
        logger.info("✅ All services initialized successfully")
        threading.Thread(target=lambda: asyncio.run(error_notifier.notify_startup())).start()
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

    async def process_and_post_task(payload, url):
        """Process a single task from the queue"""
        try:
            product_info = await amazon_processor.process_link_with_retry(url)
            if not product_info:
                await error_notifier.notify(f"❌ Failed to extract product information for {url}")
                return
            product_info['original_text'] = payload.get('original_text', '')
            product_info['images'] = payload.get('images', [])
            
            # Humara corrected function call
            posting_result = channel_poster.post_to_channels(product_info)
            
            if not posting_result or not posting_result.get('success'):
                await error_notifier.notify(f"❌ Failed to post to channels for {url}: {posting_result.get('errors', 'Unknown error')}")
            else:
                await error_notifier.notify(f"✅ New link processed and posted successfully for URL: {url}")
        except Exception as e:
            await error_notifier.notify(f"❌ Unexpected error in background task for {url}: {e}", traceback_info=traceback.format_exc())

    # Aapka banaya hua behtareen queue worker
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
                logger.info("⏳ Worker resting for 3 seconds...")
                time.sleep(3)
            except Exception as e:
                logger.error(f"❌ Error in queue_worker: {e}", exc_info=True)

    worker_thread = threading.Thread(target=queue_worker, daemon=True)
    worker_thread.start()
    logger.info("✅ Queue worker thread started")

    # Aapka banaya API endpoint (Yeh bhi bohot acha hai!)
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        try:
            data = request.get_json()
            if not data or not data.get('url'):
                return jsonify({'status': 'error', 'message': 'URL is required'}), 400
            task_queue.put(data)
            return jsonify({'status': 'success', 'message': 'Request queued for processing.', 'queue_size': task_queue.qsize()}), 202
        except Exception as e:
            logger.error(f"❌ Error in /api/process: {e}")
            return jsonify({'status': 'error', 'message': f'Internal server error: {str(e)}'}), 500

    # Aapke banaye hue naye Health Check Endpoints (Yeh bhi bohot ache hain!)
    @app.route('/api/queue_status')
    def queue_status():
        return jsonify({'queue_size': task_queue.qsize(), 'worker_running': worker_thread.is_alive()})

    @app.route('/api/health')
    def health_check():
        return jsonify({'status': 'healthy', 'queue_size': task_queue.qsize()})
        
    # --- Humara purana aur stable telebot webhook logic ---
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, f"Welcome! Logic Bot is running. Current queue size: {task_queue.qsize()}")

    @app.route('/' + Config.TELEGRAM_BOT_TOKEN, methods=['POST'])
    def get_telegram_updates():
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200

    @app.route("/")
    def webhook():
        bot.remove_webhook()
        url = f'https://main-logic-bot-ditc.onrender.com/{Config.TELEGRAM_BOT_TOKEN}'
        bot.set_webhook(url=url)
        return "<h1>✅ Bot is live and webhook is set!</h1>", 200

    return app
