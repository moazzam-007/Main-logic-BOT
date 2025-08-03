import requests
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from bs4 import BeautifulSoup
from services.url_shortener import URLShortener

logger = logging.getLogger(__name__)

class AmazonProcessor:
    def __init__(self, affiliate_tag):
        self.affiliate_tag = affiliate_tag
        self.url_shortener = URLShortener()
        logger.info(f"🏷️ Amazon Processor initialized with tag: {affiliate_tag}")

    def process_link(self, url):
        """Process Amazon link and return product info with affiliate tag"""
        try:
            logger.info(f"🔄 Processing Amazon link: {url}")
            
            # Resolve redirects and get final URL
            final_url = self._resolve_redirects(url)
            
            # Add affiliate tag
            affiliate_url = self._add_affiliate_tag(final_url)
            
            # Get short URL
            short_url = self.url_shortener.shorten_url(affiliate_url)
            
            # Extract product info
            product_info = self._extract_product_info(affiliate_url)
            
            # Combine all data
            result = {
                'title': product_info.get('title', 'Amazon Product'),
                'price': product_info.get('price', 'Price not available'),
                'affiliate_link': affiliate_url,
                'short_link': short_url,  # Add TinyURL here
                'original_url': url,
                'image_url': product_info.get('image_url')
            }
            
            logger.info(f"✅ Successfully processed: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing link {url}: {e}")
            return None

    def _resolve_redirects(self, url, max_redirects=5):
        """Follow redirects to get final URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.head(url, headers=headers, allow_redirects=True, timeout=10)
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

    def _extract_product_info(self, url):
        """Extract product information from Amazon page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract price
            price = self._extract_price(soup)
            
            # Extract image
            image_url = self._extract_image(soup)
            
            return {
                'title': title,
                'price': price,
                'image_url': image_url
            }
            
        except Exception as e:
            logger.warning(f"Could not extract product info from {url}: {e}")
            return {
                'title': 'Amazon Product',
                'price': 'Price not available',
                'image_url': None
            }

    def _extract_title(self, soup):
        """Extract product title"""
        title_selectors = [
            '#productTitle',
            '.product-title',
            '[data-automation-id="product-title"]',
            'h1.a-size-large',
            'h1 span'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title:
                    return title[:100] + "..." if len(title) > 100 else title
        
        return "Amazon Product"

    def _extract_price(self, soup):
        """Extract product price"""
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '[data-automation-id="product-price"]',
            '.a-price-range',
            '.a-price'
        ]
        
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price = element.get_text().strip()
                if price and '₹' in price:
                    return price
        
        return "Price not available"

    def _extract_image(self, soup):
        """Extract product image URL"""
        image_selectors = [
            '#landingImage',
            '[data-automation-id="product-image"] img',
            '.a-dynamic-image',
            '#imgTagWrapperId img'
        ]
        
        for selector in image_selectors:
            element = soup.select_one(selector)
            if element:
                src = element.get('src') or element.get('data-src')
                if src and src.startswith('http'):
                    return src
        
        return None
