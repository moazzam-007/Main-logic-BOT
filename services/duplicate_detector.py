# file: services/duplicate_detector.py (BULLETPROOF VERSION)
import time
import logging
import re
from threading import Lock

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self, detection_hours=48):
        self.detection_seconds = detection_hours * 3600
        self.processed_links = {}  # Format: {unique_id: timestamp}
        self.lock = Lock() # Thread safety ke liye
        self.last_cleanup = time.time()

    def _get_unique_id(self, url):
        """URL ka ek unique identifier nikalta hai (ASIN ya cleaned URL)."""
        try:
            # Amazon links ke liye ASIN (sab se reliable)
            if 'amazon' in url or 'amzn.to' in url or 'a.co' in url:
                # /dp/ASIN ya /gp/product/ASIN jaise patterns se ASIN nikalein
                match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
                if match:
                    return f"asin_{match.group(1)}"
            
            # Agar ASIN na mile, ya non-Amazon link ho, to use saaf karein
            return url.split('?')[0].rstrip('/')
        except Exception:
            return url # Failsafe

    def is_duplicate(self, url):
        """Check if URL has been processed. Yeh thread-safe hai."""
        with self.lock:
            self._cleanup_old_entries()
            unique_id = self._get_unique_id(url)
            return unique_id in self.processed_links

    def mark_as_processed(self, url):
        """Mark a URL as processed. Yeh thread-safe hai."""
        with self.lock:
            unique_id = self._get_unique_id(url)
            self.processed_links[unique_id] = time.time()
            logger.info(f"✅ Marked as processed: {unique_id}")

    def _cleanup_old_entries(self):
        """Purani entries ko memory se hatayein."""
        current_time = time.time()
        # Sirf har 1 ghante mein ek baar safai karein taake performance aachi rahe
        if current_time - self.last_cleanup > 3600:
            cutoff_time = current_time - self.detection_seconds
            old_links = [uid for uid, timestamp in self.processed_links.items() if timestamp < cutoff_time]
            
            if old_links:
                for uid in old_links:
                    del self.processed_links[uid]
                logger.info(f"🧹 Cleaned up {len(old_links)} old duplicate entries.")
            
            self.last_cleanup = current_time
