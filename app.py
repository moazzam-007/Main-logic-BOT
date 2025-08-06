# app.py (FINAL - LOCK SYSTEM VERSION)
import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
import telebot
from threading import Lock # Hum sirf Lock istemal karenge

# Aapke existing services aur config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === LOCK SYSTEM ===
# Ek global lock banayein taake ek waqt mein ek hi link process ho
processing_lock = Lock()

def create_app():
    app = Flask(__name__)
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    try:
        amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
        channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
        error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
        logger.info("✅ All services initialized successfully")
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

    async def process_and_post_task(payload, url):
        """Yeh background mein chalne wala poora process hai"""
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

    def sync_task_wrapper(payload):
        """Async task ko lock ke saath ek alag thread mein chalata hai"""
        # Kaam shuru karne se pehle, lock haasil karne ka intezar karein
        logger.info(f"⏳ Waiting to acquire lock for URL: {payload.get('url')}")
        with processing_lock:
            # Jaise hi lock mile, kaam shuru karein
            logger.info(f"✅ Lock acquired. Processing URL: {payload.get('url')}")
            try:
                asyncio.run(process_and_post_task(payload, payload.get('url')))
            except Exception as e:
                logger.error(f"❌ Error in sync_task_wrapper: {e}", exc_info=True)
        # 'with' block ke khatam hote hi lock automatically aazad ho jayega
        logger.info(f"✅ Lock released for URL: {payload.get('url')}")

    # API Endpoint
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        
        logger.info(f"🔗 API Request received for URL: {data.get('url')}. Starting background thread.")
        # Har request ke liye ek naya thread banayein jo lock ka intezar karega
        threading.Thread(target=sync_task_wrapper, args=(data,)).start()
        
        return jsonify({'status': 'success', 'message': 'Request received. Processing will start shortly.'}), 202

    # Webhook aur baaki routes
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Welcome! This is the Logic Bot.")

    @app.route('/' + Config.TELEGRAM_BOT_TOKEN, methods=['POST'])
    def get_telegram_updates():
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200

    @app.route("/")
    def webhook():
        bot.remove_webhook()
        url = f'{Config.WEBHOOK_URL}/{Config.TELEGRAM_BOT_TOKEN}' 
        bot.set_webhook(url=url, secret_token=Config.TELEGRAM_SECRET_TOKEN)
        return "<h1>✅ Bot is live and webhook is set!</h1>", 200

    return app
