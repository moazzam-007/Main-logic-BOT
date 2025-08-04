import aiohttp
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

class URLShortener:
    def __init__(self):
        self.tinyurl_api_token = os.getenv('TINYURL_API_TOKEN')
        self.use_api = bool(self.tinyurl_api_token)
    
    async def shorten_url(self, url):
        """Shorten URL using TinyURL service (async)"""
        try:
            if self.use_api:
                return await self._shorten_with_api(url)
            else:
                return await self._shorten_basic(url)
        except Exception as e:
            logger.error(f"Error shortening URL {url}: {e}")
            return url  # Return original URL if shortening fails

    async def _shorten_with_api(self, url):
        """Shorten using TinyURL API (with token, async)"""
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
            
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=data, headers=headers, timeout=10) as response:
                    response.raise_for_status()
                    result = await response.json()
                    short_url = result.get('data', {}).get('tiny_url')
                    
                    if short_url:
                        logger.info(f"✅ URL shortened (API): {url} -> {short_url}")
                        return short_url
                    else:
                        logger.warning(f"API response missing short URL for: {url}")
                        return url
        except aiohttp.ClientError as e:
            logger.error(f"TinyURL API request failed for {url}: {e}")
            return await self._shorten_basic(url)  # Fallback to basic method
        except Exception as e:
            logger.error(f"TinyURL API error for {url}: {e}")
            return url
    
    async def _shorten_basic(self, url):
        """Shorten using basic TinyURL service (no token required, async)"""
        try:
            api_url = f"https://tinyurl.com/api-create.php?url={url}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=10) as response:
                    response.raise_for_status()
                    short_url = await response.text()
                    short_url = short_url.strip()
                    
                    # Validate response
                    if short_url.startswith('https://tinyurl.com/') and len(short_url) > 20:
                        logger.info(f"✅ URL shortened (basic): {url} -> {short_url}")
                        return short_url
                    else:
                        logger.warning(f"Invalid TinyURL response for {url}: {short_url}")
                        return url
        except aiohttp.ClientError as e:
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
    
    async def batch_shorten(self, urls):
        """Shorten multiple URLs (async)"""
        tasks = [self.shorten_url(url) for url in urls]
        shortened_urls = await asyncio.gather(*tasks, return_exceptions=True)
        
        results = {}
        for original, shortened in zip(urls, shortened_urls):
            results[original] = shortened if not isinstance(shortened, Exception) else original
            
        return results
