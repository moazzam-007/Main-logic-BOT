# file: services/duplicate_detector.py (Optimized Hybrid Version)

import time
import logging
import re
from threading import Lock
import requests

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self, detection_hours=48, max_entries=50000):
        self.detection_seconds = detection_hours * 3600
        self.max_entries = max_entries
        self.processed_links = {}  # {unique_id: timestamp}
        self.lock = Lock()
        self.last_cleanup = time.time()

    # ---------- Short URL Expansion ----------
    def _expand_short_url(self, url):
        """Short URLs ko expand karke final URL nikalta hai (HEAD → GET fallback)."""
        try:
            resp = requests.head(url, allow_redirects=True, timeout=5)
            return resp.url
        except requests.RequestException:
            try:
                resp = requests.get(url, allow_redirects=True, timeout=5, stream=True)
                return resp.url
            except requests.RequestException as e:
                logger.warning(f"⚠️ Could not expand short URL {url}: {e}")
                return url

    # ---------- ASIN & Unique ID ----------
    def _get_unique_id(self, url, expand=True):
        """URL ka ek unique identifier banata hai."""
        try:
            final_url = url
            if expand:
                final_url = self._expand_short_url(url)

            # Amazon links ke multiple patterns
            if 'amazon' in final_url or 'amzn.to' in final_url or 'a.co' in final_url:
                match = re.search(r'/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})', final_url)
                if match:
                    return f"asin_{match.group(1)}"

            return final_url.split('?')[0].rstrip('/')
        except Exception:
            return url

    # ---------- Duplicate Check ----------
    def is_duplicate(self, url):
        """Check if URL has been processed. Pehle fast check, phir expand."""
        base_id = url.split('?')[0].rstrip('/')

        with self.lock:
            self._cleanup_old_entries()
            if base_id in self.processed_links:
                logger.debug(f"🔁 Duplicate found (base): {base_id}")
                return True

        # Agar base id nahi mila, tab expansion karke check karo
        expanded_id = self._get_unique_id(url, expand=True)

        with self.lock:
            if expanded_id in self.processed_links:
                logger.debug(f"🔁 Duplicate found (expanded): {expanded_id}")
                return True

        return False

    # ---------- Mark Processed ----------
    def mark_as_processed(self, url):
        """Mark URL as processed (base + expanded)."""
        base_id = url.split('?')[0].rstrip('/')
        expanded_id = self._get_unique_id(url, expand=True)

        with self.lock:
            self.processed_links[base_id] = time.time()
            self.processed_links[expanded_id] = time.time()
            logger.info(f"✅ Marked as processed: {expanded_id}")

    # ---------- Cleanup ----------
    def _cleanup_old_entries(self):
        """Memory cleanup for old & excess entries."""
        current_time = time.time()

        # Time-based cleanup (once per hour)
        if current_time - self.last_cleanup > 3600:
            cutoff = current_time - self.detection_seconds
            old_links = [uid for uid, ts in self.processed_links.items() if ts < cutoff]
            for uid in old_links:
                del self.processed_links[uid]
            if old_links:
                logger.info(f"🧹 Cleaned {len(old_links)} old entries.")
            self.last_cleanup = current_time

        # Size-based cleanup
        if len(self.processed_links) > self.max_entries:
            sorted_links = sorted(self.processed_links.items(), key=lambda x: x[1])
            excess = len(sorted_links) - self.max_entries
            for uid, _ in sorted_links[:excess]:
                del self.processed_links[uid]
            logger.info(f"🗑️ Removed {excess} excess entries.")
