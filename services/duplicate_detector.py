import hashlib
import logging
from datetime import datetime, timedelta
from utils.helpers import extract_asin_from_url, clean_url_for_duplicate_check

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self, detection_hours=24):
        self.processed_links = {}  # Format: {hash: datetime}
        self.detection_hours = detection_hours
        self.cleanup_interval = 3600  # Cleanup every hour
        self.last_cleanup = datetime.now()
        
    def is_duplicate(self, url):
        """Check if URL is a duplicate within the detection window"""
        try:
            # Cleanup old entries if needed
            self._cleanup_old_entries()
            
            # Generate unique identifier for the URL
            url_hash = self._generate_url_hash(url)
            current_time = datetime.now()
            
            if url_hash in self.processed_links:
                processed_time = self.processed_links[url_hash]
                time_diff = current_time - processed_time
                
                if time_diff.total_seconds() < (self.detection_hours * 3600):
                    logger.info(f"🔍 Duplicate detected: {url} (processed {time_diff} ago)")
                    return True
            
            # Mark as processed
            self.processed_links[url_hash] = current_time
            logger.info(f"✅ New URL marked as processed: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error in duplicate detection for {url}: {e}")
            # If error, assume not duplicate to avoid blocking legitimate requests
            return False
    
    def _generate_url_hash(self, url):
        """Generate consistent hash for URL based on product identifier"""
        try:
            # Try to extract ASIN first (most reliable for Amazon products)
            asin = extract_asin_from_url(url)
            if asin:
                return f"asin_{asin}"
            
            # Fallback to cleaned URL hash
            clean_url = clean_url_for_duplicate_check(url)
            return hashlib.md5(clean_url.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating hash for {url}: {e}")
            return hashlib.md5(url.encode()).hexdigest()
    
    def _cleanup_old_entries(self):
        """Remove old entries to prevent memory bloat"""
        try:
            current_time = datetime.now()
            
            # Only cleanup if enough time has passed
            if (current_time - self.last_cleanup).total_seconds() < self.cleanup_interval:
                return
                
            cutoff_time = current_time - timedelta(hours=self.detection_hours)
            
            # Remove old entries
            old_keys = [
                key for key, timestamp in self.processed_links.items()
                if timestamp < cutoff_time
            ]
            
            for key in old_keys:
                del self.processed_links[key]
            
            if old_keys:
                logger.info(f"🧹 Cleaned up {len(old_keys)} old duplicate detection entries")
            
            self.last_cleanup = current_time
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_stats(self):
        """Get duplicate detection statistics"""
        return {
            "total_processed": len(self.processed_links),
            "detection_window_hours": self.detection_hours,
            "last_cleanup": self.last_cleanup.isoformat()
        }
    
    def force_cleanup(self):
        """Force cleanup of all entries (for testing/debugging)"""
        count = len(self.processed_links)
        self.processed_links.clear()
        logger.info(f"🧹 Force cleaned {count} duplicate detection entries")
        return count
