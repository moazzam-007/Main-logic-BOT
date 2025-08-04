from flask import Flask, request, jsonify
import logging
import os
import asyncio
from services.amazon_processor import AmazonProcessor
from services.duplicate_detector import DuplicateDetector
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize services
try:
    amazon_processor = AmazonProcessor(Config.AFFILIATE_TAG)
    # Duplicate detector ab sirf memory-based hoga, monitor bot mein
    # isliye yahan iski zaroorat nahi hai.
    # Lekin code mein logic hai, isliye hum isko rehne dete hain.
    duplicate_detector = DuplicateDetector()
    channel_poster = ChannelPoster(Config.TELEGRAM_BOT_TOKEN, Config.OUTPUT_CHANNELS)
    error_notifier = ErrorNotifier(Config.TELEGRAM_BOT_TOKEN, Config.LOG_GROUP_ID)
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Service initialization failed: {e}")
    # Error notifier ko is point par initialize nahi kiya ja sakta
    # isliye hum seedha raise kar denge
    raise

@app.route('/')
def home():
    """Home page"""
    return """
    <h1>🤖 Amazon Link Processor Bot</h1>
    <p><strong>Status:</strong> <span style="color: green;">✅ Online</span></p>
    <h2>🔧 Configuration</h2>
    <ul>
        <li><strong>Affiliate Tag:</strong> {}</li>
        <li><strong>Output Channels:</strong> {} channel(s)</li>
        <li><strong>Duplicate Detection:</strong> ✅ Enabled (on Monitor Bot)</li>
    </ul>
    <h2>📡 API Endpoints</h2>
    <ul>
        <li><code>POST /api/process</code> - Process Amazon links</li>
        <li><code>GET /api/health</code> - Health check</li>
    </ul>
    """.format(
        Config.AFFILIATE_TAG,
        len(Config.OUTPUT_CHANNELS)
    )

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'amazon_processor': 'online',
            'duplicate_detector': 'online',
            'channel_poster': 'online'
        }
    })

@app.route('/api/process', methods=['POST'])
async def process_amazon_link():
    """Process Amazon link and post to channels"""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'No JSON data provided'}), 400

    url = data.get('url')
    original_text = data.get('original_text', '')
    images = data.get('images', [])
    channel_info = data.get('channel_info', {})

    if not url:
        return jsonify({'status': 'error', 'message': 'URL is required'}), 400

    logger.info(f"🔗 Processing request for URL: {url}")
    logger.info(f"📸 Images received: {len(images)}")
    
    # Duplicate check ko Monitor Bot par transfer kar diya hai
    # Isliye yahan sirf process karenge
    
    try:
        # Process Amazon link with retry logic
        product_info = await amazon_processor.process_link_with_retry(url)
        
        if not product_info:
            error_message = f"❌ Failed to extract product information for {url}"
            await error_notifier.notify(error_message)
            return jsonify({
                'status': 'error',
                'message': 'Failed to extract product information',
                'url': url
            }), 500

        # Add original text and images to product info
        product_info['original_text'] = original_text
        product_info['images'] = images # Monitor bot se aayi images
        
        # Post to channels with retry logic
        posting_result = await channel_poster.post_to_channels_with_retry(product_info)
        
        if not posting_result or not posting_result.get('success'):
            error_message = f"❌ Failed to post to channels for {url}: {posting_result.get('errors', 'Unknown error')}"
            await error_notifier.notify(error_message)
            return jsonify({
                'status': 'error',
                'message': 'Failed to post to channels',
                'url': url
            }), 500

        logger.info(f"✅ Successfully processed and posted: {url}")

        return jsonify({
            'status': 'success',
            'message': 'Link processed and posted successfully',
            'url': product_info.get('affiliate_link', url),
            'channels_posted': posting_result.get('posted_channels', [])
        })

    except Exception as e:
        error_message = f"❌ Unexpected error in process_amazon_link: {e}"
        await error_notifier.notify(error_message, traceback_info=traceback.format_exc())
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'url': url
        }), 500
