import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def validate_request_data(data):
    """Validate incoming API request data"""
    if not isinstance(data, dict):
        return {"valid": False, "error": "Data must be a JSON object"}
    
    if 'url' not in data:
        return {"valid": False, "error": "URL is required"}
    
    url = data.get('url')
    if not url or not isinstance(url, str):
        return {"valid": False, "error": "URL must be a non-empty string"}
    
    if not is_amazon_url(url):
        return {"valid": False, "error": "URL must be an Amazon link"}
    
    return {"valid": True}

def is_amazon_url(url):
    """Check if URL is a valid Amazon URL"""
    amazon_patterns = [
        r'https?://(?:www\.)?amazon\.[a-z.]{2,6}',
        r'https?://(?:amzn\.to|a\.co)',
        r'https?://(?:www\.)?wishlink\.com'
    ]
    
    for pattern in amazon_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False

def extract_asin_from_url(url):
    """Extract ASIN from Amazon URL for duplicate detection"""
    try:
        # Common ASIN patterns in Amazon URLs
        asin_patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'[?&]asin=([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:[/?]|$)'
        ]
        
        for pattern in asin_patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # If no ASIN found, use URL hash
        return None
    except Exception as e:
        logger.error(f"Error extracting ASIN from URL {url}: {e}")
        return None

def clean_url_for_duplicate_check(url):
    """Clean URL for better duplicate detection"""
    try:
        parsed = urlparse(url)
        # Remove query parameters and fragments
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return clean_url.rstrip('/')
    except Exception as e:
        logger.error(f"Error cleaning URL {url}: {e}")
        return url

def format_channel_message(product_info):
    """Format message for channel posting"""
    title = product_info.get('title', 'Amazon Product')
    affiliate_link = product_info.get('affiliate_link', '')
    short_link = product_info.get('short_link', affiliate_link)
    
    # Create formatted message
    message = f"🛍️ **{title}**\n\n"
    message += f"[🛒 **Buy Now**]({short_link})\n\n"
    message += f"🔗 **Link:** `{short_link}`\n\n"
    message += "📝 **Note:** Copy link and always open in browser"
    
    return message

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    return re.sub(r'[^\w\s-]', '', filename).strip()
