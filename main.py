# main.py (FINAL VERSION)
import os
import logging
import threading
from app import create_app

# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# App banayein aur worker function haasil karein
app, queue_worker = create_app()

# Worker thread ko yahan start karein
if queue_worker:
    logger.info("🔧 Starting queue worker thread from main.py...")
    worker_thread = threading.Thread(target=queue_worker, daemon=False)
    worker_thread.start()
    logger.info("✅ Queue worker thread initiated.")

# Yeh hissa sirf local machine par chalane ke liye hai
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting Enhanced Affiliate Bot on port {port} in debug mode...")
    app.run(host='0.0.0.0', port=port, debug=False)
