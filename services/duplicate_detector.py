# file: services/duplicate_detector.py (FINAL EFFICIENT VERSION)
import time
from collections import deque
import logging

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self, detection_hours=48):
        self.detection_seconds = detection_hours * 3600
        self.processed_urls = {} # Format: {url: timestamp}

    def is_duplicate(self, url):
        """Check if URL has been processed and is not expired."""
        self._cleanup_old_entries()
        return url in self.processed_urls

    def mark_as_processed(self, url):
        """Mark a URL as processed with the current timestamp."""
        self.processed_urls[url] = time.time()
        logger.info(f"✅ Marked as processed: {url}")

    def _cleanup_old_entries(self):
        """Removes URLs that are older than our detection window."""
        current_time = time.time()
        # Nayi, aasan cleanup logic
        old_urls = [url for url, timestamp in self.processed_urls.items() if current_time - timestamp > self.detection_seconds]
        for url in old_urls:
            del self.processed_urls[url]
