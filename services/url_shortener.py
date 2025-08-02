import requests
import logging
import os

logger = logging.getLogger(__name__)

class URLShortener:
    def __init__(self):
        self.tinyurl_api_token = os.getenv('TINYURL_API_TOKEN')
        self.use_api = bool(self.tinyurl_api_token)
        
    def shorten_url(self, url):
        """Shorten URL using TinyURL service"""
        try:
            if self.use_api:
                return self._shorten_with_api(url)
            else:
                return self._shorten_basic(url)
        except Exception as e:
            logger.error(f"Error shortening URL {url}: {e}")
            return url  # Return original URL if shortening fails
    
    def _shorten_with_api(self, url):
        """Shorten using TinyURL API (with token)"""
        try:
            api_url = "https://api.tinyurl.com/create"
            headers = {
                'Authorization': f'Bearer {self.tinyurl_api_token}',
                'Content-Type': 'application/json'
            }
            data = {
                'url': url,
                'domain': 'tinyurl.com'
            }
            
            response = requests.post(api_url, json=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            short_url = result.get('data', {}).get('tiny_url')
            
            if short_url:
                logger.info(f"✅ URL shortened (API): {url} -> {short_url}")
                return short_url
            else:
                logger.warning(f"API response missing short URL for: {url}")
                return url
                
        except requests.exceptions.RequestException as e:
            logger.error(f"TinyURL API request failed for {url}: {e}")
            return self._shorten_basic(url)  # Fallback to basic method
        except Exception as e:
            logger.error(f"TinyURL API error for {url}: {e}")
            return url
    
    def _shorten_basic(self, url):
        """Shorten using basic TinyURL service (no token required)"""
        try:
            api_url = f"https://tinyurl.com/api-create.php?url={url}"
            
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            
            short_url = response.text.strip()
            
            # Validate response
            if short_url.startswith('https://tinyurl.com/') and len(short_url) > 20:
                logger.info(f"✅ URL shortened (basic): {url} -> {short_url}")
                return short_url
            else:
                logger.warning(f"Invalid TinyURL response for {url}: {short_url}")
                return url
                
        except requests.exceptions.RequestException as e:
            logger.error(f"TinyURL basic request failed for {url}: {e}")
            return url
        except Exception as e:
            logger.error(f"TinyURL basic error for {url}: {e}")
            return url
    
    def is_shortened_url(self, url):
        """Check if URL is already a shortened URL"""
        shortened_domains = [
            'tinyurl.com', 'bit.ly', 'short.link', 'tiny.cc',
            'cutt.ly', 'rb.gy', 'is.gd', 't.co'
        ]
        
        for domain in shortened_domains:
            if domain in url.lower():
                return True
        
        return False
    
    def batch_shorten(self, urls):
        """Shorten multiple URLs"""
        results = {}
        for url in urls:
            results[url] = self.shorten_url(url)
        return results
