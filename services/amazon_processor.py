import requests
import logging
import re
import time
import random
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from services.url_shortener import URLShortener

logger = logging.getLogger(__name__)

class AmazonProcessor:
    def __init__(self, affiliate_tag):
        self.affiliate_tag = affiliate_tag
        self.url_shortener = URLShortener()
        self.session = requests.Session()
        logger.info(f"🏷️ Amazon Processor initialized with tag: {affiliate_tag}")

    def process_link(self, url):
        """Process Amazon link and return product info with affiliate tag"""
        try:
            logger.info(f"🔄 Processing Amazon link: {url}")
            
            # Add random delay to avoid detection
            time.sleep(random.uniform(1, 3))
            
            # Resolve redirects and get final URL
            final_url = self._resolve_redirects(url)
            
            # Add affiliate tag
            affiliate_url = self._add_affiliate_tag(final_url)
            
            # Extract product info BEFORE shortening
            product_info = self._extract_product_info(affiliate_url)
            
            # Get short URL
            short_url = self.url_shortener.shorten_url(affiliate_url)
            
            # Combine all data
            result = {
                'title': product_info.get('title', ''),
                'price': product_info.get('price', 'Price not available'),
                'affiliate_link': affiliate_url,
                'short_link': short_url,
                'original_url': url,
                'image_url': product_info.get('image_url')
            }
            
            logger.info(f"✅ Successfully processed: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing link {url}: {e}")
            return None

    def _resolve_redirects(self, url, max_redirects=5):
        """Follow redirects to get final URL with anti-detection"""
        try:
            headers = self._get_random_headers()
            
            # Add delay
            time.sleep(random.uniform(0.5, 1.5))
            
            response = self.session.head(url, headers=headers, allow_redirects=True, timeout=15)
            final_url = response.url
            
            logger.info(f"URL resolved: {url} -> {final_url}")
            return final_url
            
        except Exception as e:
            logger.warning(f"Could not resolve redirects for {url}: {e}")
            return url

    def _add_affiliate_tag(self, url):
        """Add affiliate tag to Amazon URL"""
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Add or replace affiliate tag
            query_params['tag'] = [self.affiliate_tag]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
            
            logger.info(f"Generated affiliate link: {new_url}")
            return new_url
            
        except Exception as e:
            logger.error(f"Error adding affiliate tag: {e}")
            return url

    def _get_random_headers(self):
        """Get random headers to avoid detection"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        }

    def _extract_product_info(self, url):
        """ENHANCED product information extraction with anti-detection"""
        try:
            headers = self._get_random_headers()
            
            # Add random delay
            time.sleep(random.uniform(2, 4))
            
            response = self.session.get(url, headers=headers, timeout=25)
            
            if response.status_code == 503:
                logger.warning(f"Amazon blocked request (503) for {url}")
                return self._default_product_info()
            elif response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return self._default_product_info()
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title with multiple fallbacks
            title = self._extract_title_enhanced(soup)
            
            # Extract price with multiple selectors
            price = self._extract_price_enhanced(soup)
            
            # Extract image with multiple methods
            image_url = self._extract_image_enhanced(soup)
            
            result = {
                'title': title,
                'price': price,
                'image_url': image_url
            }
            
            logger.info(f"📋 Extracted - Title: {title}, Price: {price}, Image: {bool(image_url)}")
            return result
            
        except Exception as e:
            logger.warning(f"Could not extract product info from {url}: {e}")
            return self._default_product_info()

    def _extract_title_enhanced(self, soup):
        """Enhanced title extraction with multiple selectors"""
        title_selectors = [
            '#productTitle',
            'h1 span#productTitle',
            'h1.a-size-large.a-spacing-none.a-color-base',
            '.product-title',
            '[data-automation-id="product-title"]',
            'h1.a-size-large',
            'h1 span',
            '.a-size-large.product-title-word-break',
            '#feature-bullets ul li span',
            '.a-unordered-list .a-list-item',
            'h1[data-automation-id="product-title"]',
            '.a-size-large.a-spacing-none.a-color-base.a-text-normal'
        ]
        
        for selector in title_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    title = element.get_text().strip()
                    if title and len(title) > 5:
                        # Clean title
                        clean_title = re.sub(r'\s+', ' ', title)
                        clean_title = clean_title.replace('\n', ' ').strip()
                        # Remove extra content
                        clean_title = re.sub(r'\(.*?\)', '', clean_title).strip()
                        if len(clean_title) > 80:
                            clean_title = clean_title[:77] + "..."
                        logger.info(f"✅ Title found with selector {selector}: {clean_title}")
                        return clean_title
            except Exception:
                continue
        
        logger.warning("❌ No title found")
        return ""

    def _extract_price_enhanced(self, soup):
        """Enhanced price extraction"""
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '.a-price-current .a-price-whole',
            '[data-automation-id="product-price"]',
            '.a-price-range',
            '.a-price.a-text-price.a-size-medium.apexPriceToPay .a-offscreen',
            '.a-price .a-price-symbol',
            'span.a-price.a-text-price.a-size-medium.apexPriceToPay',
            '.a-price-current',
            '#corePrice_feature_div .a-price .a-offscreen'
        ]
        
        for selector in price_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    if price_text and ('₹' in price_text or 'Rs' in price_text or any(char.isdigit() for char in price_text)):
                        # Clean price
                        clean_price = re.sub(r'[^\d₹Rs.,\-\s]', '', price_text).strip()
                        if clean_price:
                            logger.info(f"✅ Price found: {clean_price}")
                            return clean_price
            except Exception:
                continue
        
        logger.warning("❌ No price found")
        return "Price not available"

    def _extract_image_enhanced(self, soup):
        """Enhanced image extraction"""
        image_selectors = [
            '#landingImage',
            '[data-automation-id="product-image"] img',
            '.a-dynamic-image',
            '#imgTagWrapperId img',
            '.a-carousel-col .a-carousel-card img',
            '[data-a-dynamic-image]',
            '#main-image-container img',
            '.imageThumb img'
        ]
        
        for selector in image_selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    src = element.get('src') or element.get('data-src') or element.get('data-a-dynamic-image')
                    if src and ('amazon' in src or src.startswith('http')):
                        # Ensure HTTPS
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = 'https://images-na.ssl-images-amazon.com' + src
                        logger.info(f"✅ Image found: {src[:50]}...")
                        return src
            except Exception:
                continue
        
        logger.warning("❌ No image found")
        return None

    def _default_product_info(self):
        """Default product info when extraction fails"""
        return {
            'title': '',
            'price': 'Price not available',
            'image_url': None
        }
