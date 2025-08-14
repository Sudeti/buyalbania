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
    
    def get_sale_property_listings(self, max_pages=10):
        property_urls = []
        
        for page in range(1, max_pages + 1):
            # We KNOW the correct URL pattern, so use it directly
            if page == 1:
                url = f"{self.base_url}/properties"
            else:
                url = f"{self.base_url}/properties?page={page}"
            
            # Single request per page - no guessing needed
            try:
                response = self.session.get(url, timeout=30)
                if response.status_code == 200:
                    page_urls = self._extract_urls_from_page(response.content, url)
                    property_urls.extend(page_urls)
            except Exception as e:
                logger.error(f"Error on page {page}: {e}")
        
        return list(set(property_urls))  # Remove any duplicates
        
    
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
                'price': self._extract_price(text, soup),
                'location': self._extract_location(text),
                'neighborhood': self._extract_neighborhood(text),
                'property_type': self._extract_type(text),
                'square_meters': self._extract_area(text),
                'condition': self._extract_condition(text),
                'floor_level': self._extract_floor(text),

                'agent_name': self._extract_agent_name(soup, text),
                'agent_email': self._extract_agent_email(soup, text),
                'agent_phone': self._extract_agent_phone(soup, text),
            }
            
            # Only return if we have essential data
            if extracted_data['price'] > 0 and extracted_data['title']:
                agent_info = ""
                if extracted_data['agent_name']:
                    agent_info = f" (Agent: {extracted_data['agent_name']})"
                logger.info(f"✅ Sale property extracted: {extracted_data['title'][:50]}...{agent_info}")
                return extracted_data
            else:
                logger.debug(f"❌ Insufficient data for: {url}")
                return None
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    def _extract_agent_name(self, soup, text):
        """Extract agent name - Simple direct approach like phone extraction"""
        
        # Method 1: Look for common Albanian agent names directly in text
        # Common patterns: Name followed by job title, email, or phone
        name_patterns = [
            # Albanian agent name patterns (simple and direct)
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?@c21cpm\.al',  # Name before email
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?\+355',        # Name before phone
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?Agent',        # Name before Agent
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?Licensë',      # Name before License
            
            # Even simpler patterns
            r'([A-Z][a-z]{2,15} [A-Z][a-z]{2,15})\s*\n',      # Two capitalized words followed by newline
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                cleaned_name = self._clean_agent_name(match)
                if cleaned_name and self._is_valid_agent_name(cleaned_name):
                    logger.info(f"✅ Found agent name: {cleaned_name}")
                    return cleaned_name
        
        # Method 2: Look for names near email addresses (like phone does)
        email_matches = re.finditer(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
        for email_match in email_matches:
            # Look for name in 100 characters before the email
            start_pos = max(0, email_match.start() - 100)
            text_before_email = text[start_pos:email_match.start()]
            
            # Simple name pattern in the text before email
            name_match = re.search(r'([A-Z][a-z]{2,15} [A-Z][a-z]{2,15})', text_before_email)
            if name_match:
                cleaned_name = self._clean_agent_name(name_match.group(1))
                if cleaned_name and self._is_valid_agent_name(cleaned_name):
                    logger.info(f"✅ Found agent name near email: {cleaned_name}")
                    return cleaned_name
        
        return None

    def _extract_agent_email(self, soup, text):
        """Extract agent email - Simple direct approach like phone extraction"""
        
        # Method 1: Try HTML mailto links first (same as phone)
        email_links = soup.find_all('a', href=True)
        for link in email_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href.replace('mailto:', '').strip()
                if self._is_valid_email(email):
                    logger.info(f"✅ Found email in mailto: {email}")
                    return email.lower()
        
        # Method 2: Simple email patterns directly in text (same as phone)
        email_patterns = [
            r'([a-zA-Z0-9._%+-]+@c21cpm\.al)',     # Century21 emails first
            r'([a-zA-Z0-9._%+-]+@c21roy\.al)', 
            r'([a-zA-Z0-9._%+-]+@gmail\.com)',     # Gmail emails
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',  # Any email
        ]
        
        for pattern in email_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if self._is_valid_email(match):
                    logger.info(f"✅ Found email with pattern: {match}")
                    return match.lower()
        
        return None

    def _clean_agent_name(self, name):
        """Clean agent name - Keep it simple"""
        if not name:
            return None
        
        # Basic cleaning only
        name = name.strip()
        name = re.sub(r'[^\w\s]', ' ', name)  # Remove special chars
        name = ' '.join(name.split())         # Clean whitespace
        name = name.title()                   # Capitalize properly
        
        return name if len(name) > 3 else None

    def _is_valid_agent_name(self, name):
        """Simple name validation"""
        if not name or len(name) < 4 or len(name) > 50:
            return False
        
        words = name.split()
        if len(words) < 2:  # Must have at least first and last name
            return False
        
        # Each word should be reasonable length and start with capital
        for word in words:
            if len(word) < 2 or not word[0].isupper():
                return False
        
        return True

    def _extract_agent_phone(self, soup, text):
        """Extract agent phone - Enhanced for Albanian format"""
        
        phone_patterns = [
            # Albanian mobile format as shown in image: +355676475921
            r'\+355[6-9][0-9]{8}',  # More precise - Albanian mobile numbers
            r'355[6-9][0-9]{8}',    # Without the +
            r'0[6-9][0-9]{8}',      # Albanian domestic format
        ]
        
        # Try HTML tel: links first
        phone_links = soup.find_all('a', href=True)
        for link in phone_links:
            href = link.get('href', '')
            if href.startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                cleaned = self._clean_phone_number(phone)
                if cleaned:
                    return cleaned
        
        # Try regex patterns
        for pattern in phone_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                cleaned = self._clean_phone_number(match)
                if cleaned:
                    return cleaned
        
        return None

    def _clean_phone_number(self, phone):
        """Clean Albanian phone number"""
        if not phone:
            return None
        
        # Remove all non-digit characters except +
        phone = re.sub(r'[^\d\+]', '', phone)
        
        # Standardize Albanian mobile numbers
        if phone.startswith('355') and not phone.startswith('+'):
            phone = '+' + phone
        elif phone.startswith('06') or phone.startswith('07') or phone.startswith('08') or phone.startswith('09'):
            phone = '+355' + phone[1:]  # Remove the 0 and add country code
        elif len(phone) == 9 and phone[0] in '6789':  # 9 digits starting with 6,7,8,9
            phone = '+355' + phone
        
        # Validate Albanian mobile format: +355 followed by 9 digits starting with 6,7,8,9
        if re.match(r'\+355[6-9][0-9]{8}', phone):
            return phone
        
        return None

    def _is_valid_email(self, email):
        """Enhanced email validation"""
        if not email:
            return False
        
        # Basic email format check
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return False
        
        # Check length
        if len(email) > 100:
            return False
        
        return True

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
    
    def _extract_price(self, text, soup=None):
        """Enhanced price extraction - ALBANIAN FOCUSED WITH SMART FILTERING"""
        
        # Method 1: Try to get main property price from structured content first
        if soup:
            main_price = self._extract_main_property_price(soup)
            if main_price:
                logger.info(f"✅ Main property price found: €{main_price:,}")
                return Decimal(str(main_price))
        
        # Method 2: Filter out related properties section from text
        clean_text = self._remove_related_properties_section(text)
        
        # Albanian-specific price patterns (same as before)
        price_patterns = [
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*€',  # 220,000 €
            r'€\s*(\d{1,3}(?:[,.\s]?\d{3})*)',  # € 220,000
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*EUR',
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*euro',
            r'(\d{1,3}(?:[,.\s]?\d{3})*)\s*eur',
        ]
        
        prices_found = []
        for pattern in price_patterns:
            matches = re.findall(pattern, clean_text, re.IGNORECASE)
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
        
        if prices_found:
            main_price = max(prices_found)  # In clean text, max should be correct
            logger.info(f"✅ Price from filtered text: €{main_price:,}")
            return Decimal(str(main_price))
        
        logger.warning("❌ No valid price found")
        return Decimal('0')

    def _extract_main_property_price(self, soup):
        """Extract price from main property HTML structure - NEW METHOD"""
        
        # Look for price in main content areas (avoid related listings)
        main_selectors = [
            'h1 + *',  # Element right after main title
            '.property-price',
            '.main-price', 
            '.price-value',
            '[data-price]'
        ]
        
        for selector in main_selectors:
            try:
                elements = soup.select(selector)
                for element in elements[:3]:  # Only check first 3 matches
                    text = element.get_text(strip=True)
                    if '€' in text:
                        price = self._parse_single_price_value(text)
                        if price and 5000 <= price <= 15000000:
                            return price
            except:
                continue
        
        return None

    def _remove_related_properties_section(self, text):
        """Remove related/similar properties section - NEW METHOD"""
        
        # Find where related properties section starts
        split_indicators = [
            'ju gjithashtu mund të shikoni',  # "You may also see"
            'you may also like',
            'similar properties',
            'related properties', 
            'recommended properties',
            'shikoni edhe',
            'properties in the same area'
        ]
        
        text_lower = text.lower()
        earliest_split = len(text)
        
        for indicator in split_indicators:
            pos = text_lower.find(indicator)
            if pos != -1 and pos < earliest_split:
                earliest_split = pos
        
        # Return only main property content (before related section)
        return text[:earliest_split]

    def _parse_single_price_value(self, text):
        """Parse price from a single text element - NEW METHOD"""
        
        # Extract just the numeric part with €
        price_match = re.search(r'(\d{1,3}(?:[,.\s]?\d{3})*)', text)
        if price_match:
            try:
                price_str = re.sub(r'[,.\s]', '', price_match.group(1))
                return int(price_str)
            except:
                pass
        return None
    
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