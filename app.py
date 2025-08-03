from flask import Flask, request, jsonify
import logging
import os
from services.amazon_processor import AmazonProcessor
from services.duplicate_detector import DuplicateDetector
from services.channel_poster import ChannelPoster
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
    duplicate_detector = DuplicateDetector()
    channel_poster = ChannelPoster(Config.TELEGRAM_BOT_TOKEN, Config.OUTPUT_CHANNELS)
    logger.info("✅ All services initialized successfully")
except Exception as e:
    logger.error(f"❌ Service initialization failed: {e}")
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
        <li><strong>Duplicate Detection:</strong> ✅ Enabled</li>
    </ul>
    
    <h2>📡 API Endpoints</h2>
    <ul>
        <li><code>POST /api/process</code> - Process Amazon links</li>
        <li><code>GET /api/health</code> - Health check</li>
    </ul>
    
    <h2>📊 Recent Activity</h2>
    <p>Processed URLs: <strong>{}</strong></p>
    """.format(
        Config.AFFILIATE_TAG,
        len(Config.OUTPUT_CHANNELS),
        len(duplicate_detector.processed_links)  # ✅ FIXED: processed_links instead of processed_urls
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
def process_amazon_link():
    """Process Amazon link and post to channels"""
    try:
        # Get request data
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
        
        # Check for duplicates
        if duplicate_detector.is_duplicate(url):
            logger.info(f"🔄 Duplicate URL detected: {url}")
            return jsonify({
                'status': 'duplicate',
                'message': 'URL already processed',
                'url': url
            })
        
        # Mark as processed (already done in is_duplicate, but ensure it's marked)
        duplicate_detector.mark_as_processed(url)
        
        # Process Amazon link with retry logic
        max_attempts = 3
        product_info = None
        
        for attempt in range(max_attempts):
            try:
                product_info = amazon_processor.process_link(url)
                if product_info:
                    break
                else:
                    logger.warning(f"❌ Attempt {attempt + 1} failed for {url}: No product info returned")
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_attempts - 1:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to process link after {max_attempts} attempts',
                        'url': url
                    }), 500
        
        if not product_info:
            return jsonify({
                'status': 'error',
                'message': 'Failed to extract product information',
                'url': url
            }), 500
        
        # Add original text to product info
        product_info['original_text'] = original_text
        
        # Post to channels with retry logic
        max_attempts = 2
        posting_result = None
        
        for attempt in range(max_attempts):
            try:
                posting_result = channel_poster.post_to_channels(product_info, images)
                if posting_result and posting_result.get('success'):
                    break
                else:
                    logger.error(f"❌ Attempt {attempt + 1} failed for {url}: {posting_result.get('errors', 'Unknown error')}")
            except Exception as e:
                logger.error(f"❌ Attempt {attempt + 1} failed for {url}: {e}")
                if attempt == max_attempts - 1:
                    return jsonify({
                        'status': 'error',
                        'message': f'Failed to post after {max_attempts} attempts',
                        'url': url,
                        'errors': [str(e)]
                    }), 500
        
        if not posting_result or not posting_result.get('success'):
            return jsonify({
                'status': 'error',
                'message': 'Failed to post to channels',
                'url': url,
                'errors': posting_result.get('errors', []) if posting_result else ['Unknown posting error']
            }), 500
        
        logger.info(f"✅ Successfully processed and posted: {url}")
        
        return jsonify({
            'status': 'success',
            'message': 'Link processed and posted successfully',
            'url': product_info.get('affiliate_link', url),
            'channels_posted': posting_result.get('posted_channels', [])
        })
        
    except Exception as e:
        logger.error(f"❌ Unexpected error in process_amazon_link: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'message': f'Internal server error: {str(e)}',
            'url': data.get('url', 'unknown') if 'data' in locals() else 'unknown'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
