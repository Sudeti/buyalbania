# apps/property_ai/utils.py
"""
Utility functions for property analysis system
"""
import re
from urllib.parse import urlparse, urlunparse
import logging

logger = logging.getLogger(__name__)

def standardize_property_url(url: str) -> str:
    """
    Remove /en prefix from Century21 Albania URLs to standardize them.
    
    When users browse the English version, they get URLs with /en, but the system
    scrapes from the Albanian version. This function removes /en to avoid duplicates.
    
    Args:
        url (str): The property URL to standardize
        
    Returns:
        str: Standardized URL without /en prefix
        
    Example:
        Input:  "https://www.century21albania.com/en/property/4597436/njesi-komerciale-per-shitje-zone-premium-jordan-misja-tirane-smart117358.html"
        Output: "https://www.century21albania.com/property/4597436/njesi-komerciale-per-shitje-zone-premium-jordan-misja-tirane-smart117358.html"
    """
    if not url:
        return url
    
    try:
        # Parse the URL
        parsed = urlparse(url.strip())
        
        # Check if this is a Century21 Albania URL with /en prefix
        if 'century21albania.com' in parsed.netloc and parsed.path.startswith('/en/'):
            # Remove /en prefix from path
            path = parsed.path[3:]  # Remove '/en' prefix
            standardized_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            logger.debug(f"Standardized URL: {url} -> {standardized_url}")
            return standardized_url
        
        # For all other URLs, return as-is
        return url.strip()
        
    except Exception as e:
        logger.error(f"Error standardizing URL {url}: {e}")
        return url.strip()
