import re
import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode
from .url_shortener import URLShortener

logger = logging.getLogger(__name__)

class AmazonProcessor:
    def __init__(self, affiliate_tag="budgetlooks08-21"):
        self.affiliate_tag = affiliate_tag
        self.url_shortener = URLShortener()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        }
        self.supported_domains = [
            'amazon.com', 'amazon.in', 'amazon.co.uk', 'amazon.ca',
            'amazon.de', 'amazon.fr', 'amazon.it', 'amazon.es',
            'amzn.to', 'a.co'
        ]

    def process_link(self, url, existing_image_file_id=None):
        """Main method to process Amazon link"""
        try:
            logger.info(f"🔄 Processing Amazon link: {url}")
            
            # Step 1: Resolve URL if shortened
            resolved_url = self._resolve_url(url)
            
            # Step 2: Generate affiliate link
            affiliate_link = self.generate_affiliate_link(resolved_url)
            
            # Step 3: Extract product info (skip image if existing provided)
            product_info = self.extract_product_info(resolved_url, skip_image=bool(existing_image_file_id))
            
            # Step 4: Shorten the affiliate link
            short_link = self.url_shortener.shorten_url(affiliate_link)
            
            # Prepare result
            result = {
                'title': product_info.get('title', 'Amazon Product'),
                'image_url': product_info.get('image_url') if not existing_image_file_id else None,
                'image_file_id': existing_image_file_id,
                'affiliate_link': affiliate_link,
                'short_link': short_link or affiliate_link,
                'original_url': url,
                'is_product_link': product_info.get('is_product_link', False)
            }
            
            logger.info(f"✅ Successfully processed: {result['title']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing link {url}: {str(e)}")
            return None

    def _resolve_url(self, url):
        """Resolve shortened URLs to get final Amazon URL"""
        try:
            response = requests.get(url, headers=self.headers, allow_redirects=True, timeout=10)
            response.raise_for_status()
            final_url = response.url
            logger.info(f"URL resolved: {url} -> {final_url}")
            return final_url
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not resolve URL {url}: {e}. Using original.")
            return url

    def extract_product_info(self, url, skip_image=False):
        """Extract product information from Amazon page"""
        try:
            # Check if it's a product page
            if '/dp/' in url or '/gp/product/' in url:
                return self._scrape_product_page(url, skip_image)
            else:
                return self._scrape_general_page(url, skip_image)
        except Exception as e:
            logger.error(f"Error extracting product info from {url}: {e}")
            return {
                'title': 'Amazon Product',
                'image_url': None,
                'is_product_link': False
            }

    def _scrape_product_page(self, url, skip_image=False):
        """Scrape Amazon product page for details"""
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract title
            title_selectors = [
                '#productTitle',
                '.product-title',
                'h1.a-size-large'
            ]
            
            title = None
            for selector in title_selectors:
                title_tag = soup.select_one(selector)
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    break
            
            if not title:
                title = 'Amazon Product'

            # Extract image (if not skipping)
            image_url = None
            if not skip_image:
                image_selectors = [
                    '#landingImage',
                    '.a-dynamic-image',
                    'img[data-old-hires]',
                    '.imgTagWrapper img'
                ]
                
                for selector in image_selectors:
                    img_tag = soup.select_one(selector)
                    if img_tag:
                        image_url = img_tag.get('src') or img_tag.get('data-old-hires')
                        if image_url:
                            break

            return {
                'title': title[:100] + '...' if len(title) > 100 else title,
                'image_url': image_url,
                'is_product_link': True
            }

        except Exception as e:
            logger.error(f"Error scraping product page {url}: {e}")
            return {
                'title': 'Amazon Product',
                'image_url': None,
                'is_product_link': True
            }

    def _scrape_general_page(self, url, skip_image=False):
        """Scrape general Amazon page (offers, deals, etc.)"""
        try:
            response = requests.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')

            # Extract title from meta tags or page title
            title = None
            
            # Try meta title first
            meta_title = soup.find('meta', property='og:title')
            if meta_title and meta_title.get('content'):
                title = meta_title['content']
            
            # Try page title
            if not title and soup.title:
                title = soup.title.string
                
            # Clean up title
            if title:
                if 'Amazon.in' in title:
                    title = title.split('Amazon.in:', 1)[-1].strip()
                title = title.replace('Amazon.in', '').strip()
            
            if not title:
                title = 'Amazon Deal/Offer'

            return {
                'title': title[:100] + '...' if len(title) > 100 else title,
                'image_url': None,  # General pages don't need images
                'is_product_link': False
            }

        except Exception as e:
            logger.error(f"Error scraping general page {url}: {e}")
            return {
                'title': 'Amazon Page',
                'image_url': None,
                'is_product_link': False
            }

    def generate_affiliate_link(self, url):
        """Generate affiliate link with proper tag replacement"""
        try:
            resolved_url = self._resolve_url(url)
            parsed_url = urlparse(resolved_url)
            
            # Check if it's a supported domain
            if not any(domain in parsed_url.netloc for domain in self.supported_domains):
                logger.warning(f"Unsupported domain: {parsed_url.netloc}")
                return url
            
            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            
            # Remove existing affiliate tags and unnecessary parameters
            params_to_remove = ['tag', 'ref_', 'th', 'psc', 'linkCode', 'camp', 'creative']
            for param in params_to_remove:
                query_params.pop(param, None)
            
            # Add our affiliate tag
            query_params['tag'] = [self.affiliate_tag]
            
            # Rebuild URL
            new_query = urlencode(query_params, doseq=True)
            affiliate_url = urlunparse(parsed_url._replace(query=new_query))
            
            logger.info(f"Generated affiliate link: {affiliate_url}")
            return affiliate_url
            
        except Exception as e:
            logger.error(f"Error generating affiliate link for {url}: {e}")
            return url
