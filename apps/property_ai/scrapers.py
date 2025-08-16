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
        
        # Enhanced realistic headers
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Add request count for rotating user agents
        self.request_count = 0
    
    def _rotate_user_agent(self):
        """Rotate user agent every 50 requests to appear more human-like"""
        self.request_count += 1
        if self.request_count % 50 == 0:
            new_user_agent = random.choice(self.user_agents)
            self.session.headers.update({'User-Agent': new_user_agent})
            logger.debug(f"Rotated User-Agent to: {new_user_agent[:50]}...")
    
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
            # Rotate user agent periodically
            self._rotate_user_agent()
            
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
            
            # Extract area data (now returns both total and internal)
            area_data = self._extract_area(text)
            
            # Extract data for sale properties
            extracted_data = {
                'url': url,
                'title': self._extract_title(soup),
                'price': self._extract_price(text, soup),
                'location': self._extract_location(text),
                'neighborhood': self._extract_neighborhood(text),
                'property_type': self._extract_type(text),
                'total_area': area_data['total_area'],
                'internal_area': area_data['internal_area'],
                'square_meters': area_data['total_area'],  # Keep for backward compatibility
                'bedrooms': self._extract_bedrooms(text),
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
                if extracted_data['agent_email']:
                    agent_info += f" [Email: {extracted_data['agent_email']}]"
                if extracted_data['agent_phone']:
                    agent_info += f" [Phone: {extracted_data['agent_phone']}]"
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
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?@c21roy\.al',  # Name before c21roy email - NEW
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?\+355',        # Name before phone
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?Agent',        # Name before Agent
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?LicensÃ«',      # Name before License
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?Agjent',       # Name before Agjent - NEW
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?@century21atrium\.com',
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?@hotmail\.com', # Name before hotmail email - NEW
            r'([A-Z][a-z]+ [A-Z][a-z]+)\s*\n.*?@gmail\.com',  # Name before gmail email - NEW
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
        
        # Method 3: Look for agent names in agent section specifically
        agent_section_patterns = [
            r'Agent\s*\n\s*([A-Z][a-z]+ [A-Z][a-z]+)',  # Agent\nEdison Shehaj
            r'Agjent\s*\n\s*([A-Z][a-z]+ [A-Z][a-z]+)', # Agjent\nEdison Shehaj
        ]
        
        for pattern in agent_section_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                cleaned_name = self._clean_agent_name(match)
                if cleaned_name and self._is_valid_agent_name(cleaned_name):
                    logger.info(f"✅ Found agent name in agent section: {cleaned_name}")
                    return cleaned_name
        
        return None
        

    def _extract_agent_email(self, soup, text):
        """Extract agent email - DISABLED due to website obfuscation"""
        # Email extraction disabled - website uses obfuscation to prevent spam
        # Emails are displayed as [email protected] instead of real addresses
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
        if soup:
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
        """Basic email validation - kept for manual entry"""
        if not email:
            return False
        
        # Basic email format check
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_regex, email))

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
        """Extract location - IMPROVED WITH BETTER PRIORITY"""
        # Method 1: Look for location in title/header first (most accurate)
        title_location_patterns = [
            r'([A-Za-zë\s]+),\s*(Vlorë|Vlore|Tirana|Tiranë|Durrës|Durres|Shkodër|Shkoder)',  # Rradhimë, Vlorë
            r'([A-Za-zë\s]+)\s+(Vlorë|Vlore|Tirana|Tiranë|Durrës|Durres|Shkodër|Shkoder)',   # Rradhimë Vlorë
            r'(Vlorë|Vlore|Tirana|Tiranë|Durrës|Durres|Shkodër|Shkoder)\s+Albania',        # Vlorë Albania
        ]
        
        for pattern in title_location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the main city from the match
                for group in match.groups():
                    if group and group.lower() in ['vlorë', 'vlore', 'tirana', 'tiranë', 'durrës', 'durres', 'shkodër', 'shkoder']:
                        location = self._normalize_location_name(group)
                        logger.info(f"✅ Found location in title: {location}")
                        return location
        
        # Method 2: Look for specific location patterns in property info
        property_location_patterns = [
            r'në\s+([A-Za-zë\s]+),\s*(Vlorë|Vlore|Tirana|Tiranë|Durrës|Durres)',  # në Rradhimë, Vlorë
            r'në\s+(Vlorë|Vlore|Tirana|Tiranë|Durrës|Durres)',                   # në Vlorë
        ]
        
        for pattern in property_location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                for group in match.groups():
                    if group and group.lower() in ['vlorë', 'vlore', 'tirana', 'tiranë', 'durrës', 'durres', 'shkodër', 'shkoder']:
                        location = self._normalize_location_name(group)
                        logger.info(f"✅ Found location in property info: {location}")
                        return location
        
        # Method 3: Fallback to simple keyword search (but with better priority)
        # Check for main cities in order of importance/commonality
        main_cities = [
            ('Vlorë', 'Vlore'), ('Tirana', 'Tiranë'), ('Durrës', 'Durres'), 
            ('Shkodër', 'Shkoder'), ('Fier',), ('Korçë', 'Korce')
        ]
        
        text_lower = text.lower()
        for city_group in main_cities:
            for city in city_group:
                if city.lower() in text_lower:
                    location = self._normalize_location_name(city)
                    logger.info(f"✅ Found location via keyword search: {location}")
                    return location
        
        return "Albania"
    
    def _normalize_location_name(self, location):
        """Normalize location names to standard format"""
        location_lower = location.lower().strip()
        
        # Map variations to standard names
        location_map = {
            'vlore': 'Vlorë',
            'tirane': 'Tirana', 
            'durres': 'Durrës',
            'shkoder': 'Shkodër',
            'korce': 'Korçë',
        }
        
        return location_map.get(location_lower, location.title())
    
    def _extract_neighborhood(self, text):
        """Extract neighborhood/district information - EXPANDED"""
        # Common Albanian neighborhoods - EXPANDED LIST
        neighborhoods = [
            # Tirana neighborhoods
            'Blloku', 'Qendra', 'Don Bosko', 'Komuna e Parisit', 'Kombinat', 
            'Astir', 'Fresku', 'Paskuqan', 'Sauk', 'Lapraka', 'Kinostudio',
            'Selitë', 'Porcelan', 'Gjeni', 'Yzberisht', 'Farkë', 'Spitallë', 
            'Spitalle', 'Plazh', 'Shkoze', 'Shkozë',  # Added Shkoze/Shkozë
            
            # Durrës neighborhoods
            'Porto Romano', 'Shkembi Kavajes', 'Qerret',
            
            # Vlorë neighborhoods  
            'Jonufër', 'Skelë', 'Rradhimë', 'Radhime'  # Added Rradhimë/Radhime
        ]
        
        # Look for "ne" patterns FIRST (common in Albanian addresses like "NE RADHIME")
        ne_match = re.search(r'ne\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if ne_match:
            area_name = ne_match.group(1).strip()
            if 3 < len(area_name) < 30:
                # Normalize the case (RADHIME -> Rradhimë)
                normalized_name = self._normalize_neighborhood_name(area_name)
                logger.info(f"✅ Found neighborhood from 'ne': {normalized_name}")
                return normalized_name
        
        # Look for "Lagjja" (neighborhood) pattern
        lagjja_match = re.search(r'Lagjja\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if lagjja_match:
            neighborhood_name = lagjja_match.group(1).strip()
            if 3 < len(neighborhood_name) < 30:  # Reasonable length
                logger.info(f"✅ Found neighborhood from Lagjja: {neighborhood_name}")
                return neighborhood_name
        
        # Look for "tek" patterns (common in Albanian addresses)
        tek_match = re.search(r'tek\s+([A-Za-zë\s]+)', text, re.IGNORECASE)
        if tek_match:
            area_name = tek_match.group(1).strip()
            if 3 < len(area_name) < 30:
                logger.info(f"✅ Found neighborhood from 'tek': {area_name}")
                return area_name
        
        # Look for neighborhood keywords in text
        text_lower = text.lower()
        for neighborhood in neighborhoods:
            if neighborhood.lower() in text_lower:
                logger.info(f"✅ Found neighborhood: {neighborhood}")
                return neighborhood
        
        return None  # Return None for nullable field
    
    def _normalize_neighborhood_name(self, name):
        """Normalize neighborhood names to standard format"""
        name_lower = name.lower().strip()
        
        # Map variations to standard names
        neighborhood_map = {
            'radhime': 'Rradhimë',
            'shkoze': 'Shkozë',
            'vlore': 'Vlorë',
            'tirane': 'Tirana',
            'durres': 'Durrës',
            'shkoder': 'Shkodër',
            'korce': 'Korçë',
        }
        
        return neighborhood_map.get(name_lower, name.title())

    def _extract_type(self, text):
        """Extract property type - RESPECTS LLOJI FIELD"""
        text_lower = text.lower()
        
        # Method 1: Look for "Lloji" (Type) field first - MOST ACCURATE
        lloji_patterns = [
            r'lloji\s*:\s*([a-zA-Zë]+)',  # Lloji: Apartament
            r'lloji\s+([a-zA-Zë]+)',      # Lloji Apartament
            r'type\s*:\s*([a-zA-Zë]+)',   # Type: Apartment
            r'type\s+([a-zA-Zë]+)',       # Type Apartment
        ]
        
        for pattern in lloji_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                property_type = match.group(1).strip().lower()
                logger.info(f"✅ Found property type from Lloji field: {property_type}")
                
                # Map Albanian types to our categories - RESPECT THE LLOJI FIELD
                if 'apartament' in property_type:
                    return 'apartment'
                elif 'studio' in property_type:
                    return 'studio'
                elif any(word in property_type for word in ['villa', 'vilë', 'shtëpi', 'shtepi']):
                    return 'villa'
                elif any(word in property_type for word in ['dyqan', 'magazinë', 'komercial']):
                    return 'commercial'
                elif any(word in property_type for word in ['zyre', 'office']):
                    return 'office'
                elif any(word in property_type for word in ['truall', 'toke', 'tokë']):
                    return 'land'
        
        # Method 2: Fallback to keyword search if no Lloji field found
        if 'apartament' in text_lower:
            return 'apartment'
        elif 'studio' in text_lower:
            return 'studio'
        elif any(word in text_lower for word in ['villa', 'vilë', 'shtëpi', 'shtepi', 'house']):
            return 'villa'
        elif any(word in text_lower for word in ['dyqan', 'magazinë', 'magazine', 'komercial', 'biznesi']):
            return 'commercial'
        elif any(phrase in text_lower for phrase in ['zyra pune', 'office space', 'zyre pune', 'biznes zyre']):
            return 'office'
        elif any(word in text_lower for word in ['truall', 'toke', 'tokë', 'land']):
            return 'land'
        
        return 'residential'  # Default fallback
    
    def _extract_area(self, text):
        """Enhanced area extraction for Albanian format - NOW EXTRACTS BOTH TOTAL AND INTERNAL"""
        # First, clean the text to remove related properties section
        clean_text = self._remove_related_properties_section(text)
        
        total_area = None
        internal_area = None
        
        # Extract total area (Sip. Totale) - MORE SPECIFIC PATTERNS
        total_patterns = [
            r'Sip\.\s*Totale\s*(\d+)\s*m[²2]?',  # Sip. Totale 73m2
            r'sipërfaqe\s*totale[:\s]*(\d+)\s*m[²2]?',  # sipërfaqe totale: 73m2
            r'total\s*area[:\s]*(\d+)\s*m[²2]?',  # total area: 73m2
            r'sipërfaqe\s*bruto[:\s]*(\d+)\s*m[²2]?',  # sipërfaqe bruto: 73m2 (from description)
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                try:
                    total_area = int(match.group(1))
                    if 10 <= total_area <= 5000:  # Reasonable range
                        logger.info(f"✅ Found total area: {total_area}m²")
                        break
                except:
                    continue
        
        # Extract internal area (Sip. e brendshme) - MORE SPECIFIC PATTERNS
        internal_patterns = [
            r'Sip\.\s*e\s*brendshme\s*(\d+)\s*m[²2]?',  # Sip. e brendshme 65m2
            r'Sip\.\s*e\s*brendshme\s+(\d+)\s*m[²2]?',  # Sip. e brendshme  151m2 (extra spaces)
            r'sipërfaqe\s*e\s*brendshme[:\s]*(\d+)\s*m[²2]?',  # sipërfaqe e brendshme: 65m2
            r'internal\s*area[:\s]*(\d+)\s*m[²2]?',  # internal area: 65m2
            r'usable\s*area[:\s]*(\d+)\s*m[²2]?',  # usable area: 65m2
            r'sipërfaqe\s*neto[:\s]*(\d+)\s*m[²2]?',  # sipërfaqe neto: 65m2 (from description)
        ]
        
        for pattern in internal_patterns:
            match = re.search(pattern, clean_text, re.IGNORECASE)
            if match:
                try:
                    internal_area = int(match.group(1))
                    if 10 <= internal_area <= 5000:  # Reasonable range
                        logger.info(f"✅ Found internal area: {internal_area}m²")
                        break
                except:
                    continue
        
        # Fallback: if we only found one type, try generic patterns in main content only
        if not total_area and not internal_area:
            # Look for area in the main property info section (before related properties)
            main_content = clean_text[:2000]  # First 2000 chars should contain main property info
            
            generic_patterns = [
                r'(\d+)\s*m[²2]',  # Generic format
                r'(\d+)\s*metr.*katror',  # Albanian "square meters"
                r'(\d+)\s*m2',  # Simple m2
            ]
            
            areas_found = []
            for pattern in generic_patterns:
                matches = re.findall(pattern, main_content, re.IGNORECASE)
                for match in matches:
                    try:
                        area = int(match)
                        if 10 <= area <= 5000:  # Reasonable range
                            areas_found.append(area)
                    except:
                        continue
            
            if areas_found:
                # If we found multiple areas, assume the larger one is total
                areas_found.sort()
                if len(areas_found) >= 2:
                    internal_area = areas_found[0]  # Smaller
                    total_area = areas_found[-1]    # Larger
                    logger.info(f"✅ Fallback: internal={internal_area}m², total={total_area}m²")
                else:
                    total_area = areas_found[0]
                    logger.info(f"✅ Fallback: total area only: {total_area}m²")
        
        return {
            'total_area': total_area,
            'internal_area': internal_area
        }
    
    def _extract_condition(self, text):
        """Extract new/used condition - IMPROVED ALBANIAN DETECTION"""
        text_lower = text.lower()
        
        # Look for "Statusi" field first (most accurate)
        status_patterns = [
            r'statusi\s*:\s*([a-zA-Zë\s]+)',  # Statusi: I Perdorur
            r'statusi\s+([a-zA-Zë\s]+)',      # Statusi I Perdorur
            r'status\s*:\s*([a-zA-Zë\s]+)',   # Status: Used
            r'status\s+([a-zA-Zë\s]+)',       # Status Used
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                status = match.group(1).strip().lower()
                logger.info(f"✅ Found status from Statusi field: {status}")
                
                if any(word in status for word in ['i ri', 'new', 'sapoperfunduar', 'modern']):
                    return 'new'
                elif any(word in status for word in ['i perdorur', 'used', 'renovated']):
                    return 'used'
        
        # Fallback to keyword search
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
    
    def _extract_bedrooms(self, text):
        """Extract number of bedrooms"""
        text_lower = text.lower()
        
        # Look for bedroom patterns in Albanian
        bedroom_patterns = [
            r'dhomat\s+e\s+gjumit\s*(\d+)',  # Dhomat e gjumit 1
            r'dhoma\s+e\s+gjumit\s*(\d+)',   # Dhoma e gjumit 1
            r'bedrooms?\s*(\d+)',            # Bedrooms 1
            r'bedroom\s*(\d+)',              # Bedroom 1
        ]
        
        for pattern in bedroom_patterns:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    bedrooms = int(match.group(1))
                    if 0 <= bedrooms <= 20:  # Reasonable range
                        logger.info(f"✅ Found bedrooms: {bedrooms}")
                        return bedrooms
                except:
                    continue
        
        # Look for apartment type patterns like "1+1+2" (1 bedroom, 1 living room, 2 balconies)
        apartment_pattern = re.search(r'(\d+)\+(\d+)\+(\d+)', text)
        if apartment_pattern:
            try:
                bedrooms = int(apartment_pattern.group(1))
                if 0 <= bedrooms <= 20:
                    logger.info(f"✅ Found bedrooms from apartment type: {bedrooms}")
                    return bedrooms
            except:
                pass
        
        return None


# Backward compatibility
Century21Scraper = Century21AlbaniaScraper