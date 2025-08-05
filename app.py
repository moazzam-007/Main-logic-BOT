import os
import logging
import asyncio
import traceback
import threading
from flask import Flask, request, jsonify
import telebot # Bot wali library

# Aapke existing services aur config
from services.amazon_processor import AmazonProcessor
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_app():
    # Initialize Flask app
    app = Flask(__name__)
    
    # Initialize Bot
    bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)
    
    # Initialize services
    try:
        amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
        # === CHANGE KIYA GAYA HAI (1) ===
        # Ab hum ChannelPoster ko poora bot object de rahe hain, token nahi.
        channel_poster = ChannelPoster(bot, Config.OUTPUT_CHANNELS)
        error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.ERROR_CHAT_ID)
        logger.info("✅ All services initialized successfully")
        
        # Startup notification ko alag thread mein bhejte hain taake startup block na ho
        threading.Thread(target=lambda: asyncio.run(error_notifier.notify_startup())).start()
        
    except Exception as e:
        logger.error(f"❌ Service initialization failed: {e}")
        raise

    # === BACKGROUND TASK LOGIC (TO PREVENT 502 ERROR) ===
    def run_async_task(target_func, *args):
        # Yeh function async code ko ek alag thread mein chalata hai
        def task_wrapper():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(target_func(*args))
            finally:
                loop.close()
        
        thread = threading.Thread(target=task_wrapper)
        thread.start()

    async def process_and_post_task(payload, url):
        # Yeh background mein chalne wala poora process hai
        try:
            product_info = await amazon_processor.process_link_with_retry(url)
            if not product_info:
                error_message = f"❌ Failed to extract product information for {url}"
                await error_notifier.notify(error_message)
                return

            product_info['original_text'] = payload.get('original_text', '')
            product_info['images'] = payload.get('images', [])
            
            # === CHANGE KIYA GAYA HAI (2) ===
            # Function ka naam theek kar diya gaya hai aur 'await' hata diya gaya hai
            posting_result = channel_poster.post_to_channels(product_info)
            
            if not posting_result or not posting_result.get('success'):
                error_message = f"❌ Failed to post to channels for {url}: {posting_result.get('errors', 'Unknown error')}"
                await error_notifier.notify(error_message)
            else:
                logger.info(f"✅ Successfully processed and posted: {url}")
                await error_notifier.notify(f"✅ New link processed and posted successfully for URL: {url}")
        except Exception as e:
            error_message = f"❌ Unexpected error in background task for {url}: {e}"
            await error_notifier.notify(error_message, traceback_info=traceback.format_exc())


    # === API ENDPOINT FOR MONITOR BOT ===
    @app.route('/api/process', methods=['POST'])
    def process_amazon_link_api():
        data = request.get_json()
        if not data or not data.get('url'):
            return jsonify({'status': 'error', 'message': 'URL is required'}), 400
        
        url = data.get('url')
        logger.info(f"🔗 API Request received for URL: {url}. Starting background processing.")
        
        # Foran response bhejein aur kaam background mein shuru karein
        run_async_task(process_and_post_task, data, url)
        
        return jsonify({'status': 'success', 'message': 'Request received. Processing in background.'}), 202

    # === TELEGRAM BOT LOGIC (WEBHOOK) ===
    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        bot.reply_to(message, "Welcome! This is the Logic Bot.")

    # Yahan aap apne purane /exchange command waghera add kar sakte hain

    @app.route('/' + Config.TELEGRAM_BOT_TOKEN, methods=['POST'])
    def get_telegram_updates():
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200

    @app.route("/")
    def webhook():
        bot.remove_webhook()
        # Yahan apne logic-bot ka URL daalein
        url = f'https://main-logic-bot-ditc.onrender.com/{Config.TELEGRAM_BOT_TOKEN}' 
        bot.set_webhook(url=url)
        return "<h1>✅ Bot is live and webhook is set!</h1>", 200

    return app
