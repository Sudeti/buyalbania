# Updated scrapers.py - IMPROVED ALBANIAN DETECTION
import requests
from bs4 import BeautifulSoup
import re
import time
import logging
from decimal import Decimal
from urllib.parse import urljoin
import random

logger = logging.getLogger(__name__)

class Century21AlbaniaScraper:
    def __init__(self):
        self.base_url = "https://www.century21albania.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_sale_property_listings(self, max_pages=10, property_types=None):
        """Get sale property URLs - IMPROVED"""
        property_urls = []
        
        for page in range(1, max_pages + 1):
            urls_to_try = [
                f"{self.base_url}/properties",
                f"{self.base_url}/properties?page={page}",
                f"{self.base_url}/en/properties?page={page}",
                f"{self.base_url}/properties/for-sale?page={page}",  # Try sale-specific URL
            ]
            
            for url in urls_to_try:
                try:
                    response = self.session.get(url, timeout=30)
                    if response.status_code == 200:
                        page_urls = self._extract_urls_from_page(response.content, url)
                        if page_urls:
                            property_urls.extend(page_urls)
                            break
                except Exception as e:
                    logger.error(f"Error getting page {url}: {e}")
            
            time.sleep(random.uniform(1, 3))
        
        return list(set(property_urls))
    
    def _extract_urls_from_page(self, html_content, page_url):
        """Extract property URLs from listings page"""
        soup = BeautifulSoup(html_content, 'html.parser')
        urls = []
        
        # Find all property links
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/property/' in href or 'smart' in href:
                full_url = urljoin(page_url, href)
                urls.append(full_url)
        
        return urls
    
    def scrape_property(self, url):
        """Scrape basic property data - IMPROVED ALBANIAN DETECTION"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # IMPROVED: More accurate Albanian rental detection
            rental_keywords = [
                'qira', 'për qira', 'for rent', 'jepet me qira', 'me qera', 
                'jepet me qera', 'rent', 'rental'
            ]
            
            # IMPROVED: More accurate Albanian sale detection  
            sale_keywords = [
                'shesim', 'shitje', 'shitet', 'për shitje', 'for sale',
                'ne shitje', 'në shitje', 'sell', 'selling'
            ]
            
            text_lower = text.lower()
            url_lower = url.lower()
            
            # Check rental indicators
            is_rental = any(keyword in text_lower for keyword in rental_keywords)
            
            # Check sale indicators in both text and URL
            is_sale = (
                any(keyword in text_lower for keyword in sale_keywords) or
                any(keyword in url_lower for keyword in ['shitet', 'shitje', 'shesim'])
            )
            
            # Skip if clearly rental and no sale indicators
            if is_rental and not is_sale:
                logger.debug(f"Skipping rental property: {url}")
                return None
                
            # Skip if no clear sale indicators (be more strict)
            if not is_sale:
                logger.debug(f"No sale indicators found: {url}")
                return None
            
            # Extract data for sale properties
            extracted_data = {
                'url': url,
                'title': self._extract_title(soup),
                'price': self._extract_price(text),
                'location': self._extract_location(text),
                'neighborhood': self._extract_neighborhood(text),
                'property_type': self._extract_type(text),
                'square_meters': self._extract_area(text),
                'condition': self._extract_condition(text),
                'floor_level': self._extract_floor(text),
            }
            
            # Only return if we have essential data
            if extracted_data['price'] > 0 and extracted_data['title']:
                logger.info(f"✅ Sale property extracted: {extracted_data['title'][:50]}...")
                return extracted_data
            else:
                logger.debug(f"❌ Insufficient data for: {url}")
                return None
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _extract_title(self, soup):
        """Extract title - IMPROVED ALBANIAN"""
        # Try multiple selectors
        title_selectors = ['h1', '.property-title', '.title', '.property-name']
        
        for selector in title_selectors:
            element = soup.find(selector)
            if element:
                title = element.get_text(strip=True)
                # Clean up Albanian-specific formatting
                title = re.sub(r'\s+', ' ', title)  # Multiple spaces
                title = title.replace('SHITET', '').replace('SHITJE', '').strip()
                if title and len(title) > 5:
                    return title[:500]
        
        # Fallback to page title
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True).split('–')[0].split('|')[0]
            return title[:500]
        
        return "Property"
    
    def _extract_price(self, text):
        """Enhanced price extraction - ALBANIAN FOCUSED"""
        # Albanian-specific price patterns
        price_patterns = [
            r'çmimi[:\s]*€?\s*(\d{1,3}(?:[,.\s]?\d{3})*)',  # Albanian "price"
            r'vlera[:\s]*€?\s*(\d{1,3}(?:[,.\s]?\d{3})*)',   # Albanian "value"
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*€',  # 220,000 €
            r'€\s*(\d{1,3}(?:[,.\s]?\d{3})*)',  # € 220,000
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*EUR',
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*euro',
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*eur',
        ]
        
        prices_found = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Clean and convert
                    price_str = re.sub(r'[,.\s]', '', match)
                    price = int(price_str)
                    # Albanian property price range
                    if 5000 <= price <= 15000000:  # €5K to €15M
                        prices_found.append(price)
                except:
                    continue
        
        return Decimal(str(max(prices_found))) if prices_found else Decimal('0')
    
    def _extract_location(self, text):
        """Extract location - MORE FLEXIBLE"""
        # Main Albanian cities and areas
        locations = [
            'Tirana', 'Tiranë', 'Durrës', 'Durres', 'Vlorë', 'Vlore', 
            'Shkodër', 'Shkoder', 'Paskuqan', 'Elbasan', 'Kamëz', 'Kamez',
            'Fier', 'Korçë', 'Korce', 'Kavajë', 'Kavaje', 'Lezhë', 'Lezhe'
        ]
        
        text_lower = text.lower()
        for location in locations:
            if location.lower() in text_lower:
                return location
        
        # Look for patterns like "në [Location]"
        location_match = re.search(r'në\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if location_match:
            potential_location = location_match.group(1).strip()
            if 3 < len(potential_location) < 20:  # Reasonable length
                return potential_location.title()
        
        return "Albania"
    
    def _extract_neighborhood(self, text):
        """Extract neighborhood/district information - EXPANDED"""
        # Common Albanian neighborhoods - EXPANDED LIST
        neighborhoods = [
            # Tirana neighborhoods
            'Blloku', 'Qendra', 'Don Bosko', 'Komuna e Parisit', 'Kombinat', 
            'Astir', 'Fresku', 'Paskuqan', 'Sauk', 'Lapraka', 'Kinostudio',
            'Selitë', 'Porcelan', 'Gjeni', 'Yzberisht', 'Farkë', 'Spitallë', 
            'Spitalle', 'Plazh',
            
            # Durrës neighborhoods
            'Porto Romano', 'Shkembi Kavajes', 'Qerret',
            
            # Vlorë neighborhoods  
            'Jonufër', 'Skelë'
        ]
        
        text_lower = text.lower()
        for neighborhood in neighborhoods:
            if neighborhood.lower() in text_lower:
                return neighborhood
        
        # Look for "Lagjja" (neighborhood) pattern
        lagjja_match = re.search(r'Lagjja\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if lagjja_match:
            neighborhood_name = lagjja_match.group(1).strip()
            if 3 < len(neighborhood_name) < 30:  # Reasonable length
                return neighborhood_name
        
        # Look for "tek" patterns (common in Albanian addresses)
        tek_match = re.search(r'tek\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if tek_match:
            area_name = tek_match.group(1).strip()
            if 3 < len(area_name) < 30:
                return area_name
        
        return None  # Return None for nullable field

    def _extract_type(self, text):
        """Extract property type - IMPROVED"""
        text_lower = text.lower()
        
        # Check in order of specificity
        if any(word in text_lower for word in ['dyqan', 'magazinë', 'magazine', 'komercial', 'biznesi']):
            return 'commercial'
        elif any(word in text_lower for word in ['zyre', 'office', 'zyra']):
            return 'office'
        elif any(word in text_lower for word in ['villa', 'vilë', 'shtëpi', 'shtepi', 'house']):
            return 'villa'
        elif 'apartament' in text_lower:
            return 'apartment'
        elif 'studio' in text_lower:
            return 'studio'
        elif any(word in text_lower for word in ['truall', 'toke', 'land']):
            return 'land'
        
        return 'residential'  # Default fallback
    
    def _extract_area(self, text):
        """Enhanced area extraction for Albanian format"""
        patterns = [
            r'Sip\.\s*(?:Totale|e brendshme|totale)\s*(\d+)\s*m[²2]?',  # Albanian format
            r'sipërfaqe[:\s]*(\d+)\s*m[²2]?',  # Albanian "surface area"
            r'(\d+)\s*m[²2]',  # Generic format
            r'(\d+)\s*metr.*katror',  # Albanian "square meters"
            r'(\d+)\s*m2',  # Simple m2
        ]
        
        areas_found = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    area = int(match)
                    if 10 <= area <= 5000:  # Reasonable range
                        areas_found.append(area)
                except:
                    continue
        
        # Return largest area found (likely total area)
        return max(areas_found) if areas_found else None
    
    def _extract_condition(self, text):
        """Extract new/used condition"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['i ri', 'new', 'sapoperfunduar', 'modern']):
            return 'new'
        elif any(word in text_lower for word in ['i perdorur', 'used', 'renovated']):
            return 'used'
        
        return 'used'  # Default
    
    def _extract_floor(self, text):
        """Extract floor level"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['kati 0', 'përdhe', 'ground', 'përdhesa']):
            return 'ground_floor'
        elif any(word in text_lower for word in ['kati 1', 'katin e parë']):
            return 'first_floor'
        
        # Look for floor numbers
        match = re.search(r'kati\s*(\d+)', text_lower)
        if match:
            return f'floor_{match.group(1)}'
        
        return ''

# Backward compatibility
Century21Scraper = Century21AlbaniaScraper