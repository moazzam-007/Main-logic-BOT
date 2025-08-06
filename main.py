# main.py (Final Simple Version)
from app import create_app
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("🔧 Creating Flask app instance for Gunicorn...")
app = create_app()
logger.info("✅ Flask app instance created.")

# Local testing ke liye
if __name__ == '__main__':
    logger.info(f"🚀 Starting Bot locally...")
    app.run(host='0.0.0.0', port=5000, debug=True)
