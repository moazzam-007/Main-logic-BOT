import os
import logging
import json
from flask import Flask, request, jsonify, render_template
from services.amazon_processor import AmazonProcessor
from services.duplicate_detector import DuplicateDetector
from services.channel_poster import ChannelPoster
from services.error_notifier import ErrorNotifier
from utils.config import Config
from utils.helpers import validate_request_data

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder='templates')

# Initialize services
config = Config()
amazon_processor = AmazonProcessor(config.AFFILIATE_TAG)
duplicate_detector = DuplicateDetector()
channel_poster = ChannelPoster(config.BOT_TOKEN, config.CHANNEL_IDS)
error_notifier = ErrorNotifier(config.BOT_TOKEN, config.ERROR_CHAT_ID) if hasattr(config, 'ERROR_CHAT_ID') else None

@app.route('/api/process', methods=['POST'])
def process_amazon_link():
    """Main API endpoint to process Amazon links from monitor bot"""
    try:
        # Get JSON data
        data = request.get_json()
        if not data:
            logger.warning("No data received in API request")
            return jsonify({"status": "error", "message": "No data provided"}), 400

        # Extract data from monitor bot
        url = data.get('url')
        original_text = data.get('original_text', '')
        images = data.get('images', [])  # Images from monitor bot
        channel_info = data.get('channel_info', {})

        logger.info(f"🔗 Processing request for URL: {url}")
        logger.info(f"📸 Images received: {len(images)}")

        # Check for duplicates
        if duplicate_detector.is_duplicate(url):
            logger.info(f"⚠️ Duplicate URL detected, skipping: {url}")
            return jsonify({
                "status": "duplicate", 
                "message": "Duplicate URL detected",
                "url": url
            }), 200

        # Process with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Process Amazon link
                result = amazon_processor.process_link(url)
                if not result:
                    raise Exception("Failed to process Amazon link")

                # Create product info for posting
                product_info = {
                    'title': result.get('title', 'Amazon Product'),
                    'price': result.get('price', 'Price not available'),
                    'affiliate_link': result.get('affiliate_link', url),
                    'original_text': original_text,
                    'image_url': result.get('image_url'),
                    'image_file_id': result.get('image_file_id')
                }

                # Post to channels with images
                posting_result = channel_poster.post_to_channels(product_info, images)
                
                if posting_result['success']:
                    logger.info(f"✅ Successfully processed and posted: {url}")
                    return jsonify({
                        "status": "success",
                        "message": "Link processed and posted successfully", 
                        "url": result.get('affiliate_link', url),
                        "channels_posted": posting_result['posted_channels']
                    }), 200
                else:
                    raise Exception(f"Failed to post to channels: {posting_result['error']}")

            except Exception as e:
                logger.error(f"❌ Attempt {attempt+1} failed for {url}: {str(e)}")
                if attempt == max_retries - 1:
                    # Final attempt failed, notify error
                    if error_notifier and hasattr(error_notifier, 'notify_error'):
                        error_notifier.notify_error(url, str(e), original_text)
                    
                    return jsonify({
                        "status": "error",
                        "message": f"Processing failed after {max_retries} attempts: {str(e)}",
                        "url": url
                    }), 500
                continue
                
    except Exception as e:
        logger.error(f"❌ General API error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Enhanced Affiliate Bot is running! 🤖",
        "services": {
            "bot_token_set": bool(config.BOT_TOKEN and config.BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE'),
            "channels_configured": len(config.CHANNEL_IDS) > 0,
            "affiliate_tag_set": bool(config.AFFILIATE_TAG)
        }
    })

@app.route('/')
def home():
    """Dashboard home page"""
    stats = {
        "processed_links": len(duplicate_detector.processed_links),
        "channels_configured": len(config.CHANNEL_IDS),
        "affiliate_tag": config.AFFILIATE_TAG
    }
    return render_template('index.html', stats=stats)

@app.route('/api/stats')
def get_stats():
    """Get processing statistics"""
    return jsonify({
        "processed_links_count": len(duplicate_detector.processed_links),
        "channels_configured": len(config.CHANNEL_IDS),
        "duplicate_detection_active": True
    })

if __name__ == '__main__':
    app.run(debug=True)
