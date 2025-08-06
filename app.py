import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
import telebot
from threading import Lock # === LOCK SYSTEM (Step 1: Lock Ko Import Karein) ===

# Aapke existing services aur config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# === LOCK SYSTEM (Step 2: Global Lock Banayein) ===
# Yeh lock yakeeni banayega ke ek waqt mein ek hi link process ho
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

    # === LOCK SYSTEM (Step 3: Worker Ko Lock Istemal Karna Sikhayein) ===
    def run_async_task(target_func, *args):
        def task_wrapper():
            # Kaam shuru karne se pehle, lock haasil karne ka intezar karein
            logger.info("⏳ Waiting to acquire lock to process a new link...")
            with processing_lock:
                # Jaise hi lock mile, kaam shuru karein
                logger.info("✅ Lock acquired. Processing link.")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(target_func(*args))
                finally:
                    loop.close()
            # 'with' block ke khatam hote hi lock automatically aazad ho jayega
            logger.info("✅ Lock released. Ready for the next link.")
        
        thread = threading.Thread(target=task_wrapper)
        thread.start()

    async def process_and_post_task(payload, url):
        # Is function mein koi change nahi hai
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

    # API Endpoint (Isme koi change nahi)
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        
        url = data.get('url')
        logger.info(f"🔗 API Request received for URL: {url}. Starting background processing.")
        
        run_async_task(process_and_post_task, data, url)
        
        return jsonify({'status': 'success', 'message': 'Request received. Processing in background.'}), 202

    # Webhook aur baaki routes (Inme koi change nahi)
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
        url = f'https://main-logic-bot-ditc.onrender.com/{Config.TELEGRAM_BOT_TOKEN}' 
        bot.set_webhook(url=url)
        return "<h1>✅ Bot is live and webhook is set!</h1>", 200

    return app
