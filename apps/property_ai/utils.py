# apps/property_ai/utils.py
"""
Utility functions for property analysis system
"""
import re
from urllib.parse import urlparse, urlunparse
import logging
import time
import logging
from functools import wraps
from django.core.cache import cache
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)

def performance_monitor(func_name=None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_queries = len(connection.queries)
            
            try:
                result = func(*args, **kwargs)
                success = True
            except Exception as e:
                success = False
                raise
            finally:
                end_time = time.time()
                end_queries = len(connection.queries)
                
                duration = end_time - start_time
                query_count = end_queries - start_queries
                
                name = func_name or f"{func.__module__}.{func.__name__}"
                
                # Log performance metrics
                if duration > 1.0:  # Log slow operations
                    logger.warning(f"SLOW OPERATION: {name} took {duration:.2f}s ({query_count} queries)")
                elif duration > 0.5:  # Log moderately slow operations
                    logger.info(f"MODERATE: {name} took {duration:.2f}s ({query_count} queries)")
                else:
                    logger.debug(f"FAST: {name} took {duration:.3f}s ({query_count} queries)")
                
                # Track cache performance
                cache_hits = getattr(wrapper, 'cache_hits', 0)
                cache_misses = getattr(wrapper, 'cache_misses', 0)
                if cache_hits + cache_misses > 0:
                    hit_rate = (cache_hits / (cache_hits + cache_misses)) * 100
                    logger.debug(f"CACHE STATS for {name}: {hit_rate:.1f}% hit rate ({cache_hits} hits, {cache_misses} misses)")
            
            return result
        return wrapper
    return decorator

def cache_performance_monitor(cache_key, timeout=3600):
    """Decorator to monitor cache performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                # Cache hit
                wrapper.cache_hits = getattr(wrapper, 'cache_hits', 0) + 1
                logger.debug(f"Cache HIT: {cache_key}")
                return cached_result
            
            # Cache miss - execute function
            wrapper.cache_misses = getattr(wrapper, 'cache_misses', 0) + 1
            logger.debug(f"Cache MISS: {cache_key}")
            
            result = func(*args, **kwargs)
            
            # Cache the result
            if result is not None:
                cache.set(cache_key, result, timeout)
                logger.debug(f"Cache SET: {cache_key} (timeout: {timeout}s)")
            
            return result
        return wrapper
    return decorator

def get_performance_stats():
    """Get current performance statistics"""
    stats = {
        'cache_stats': {},
        'slow_operations': [],
        'database_queries': len(connection.queries),
    }
    
    # Get cache statistics if available
    try:
        cache_stats = cache.get('performance_stats', {})
        stats['cache_stats'] = cache_stats
    except:
        pass
    
    return stats

def log_system_health():
    """Log system health metrics"""
    try:
        from .models import PropertyAnalysis
        
        # Database stats
        total_properties = PropertyAnalysis.objects.count()
        completed_analyses = PropertyAnalysis.objects.filter(status='completed').count()
        failed_analyses = PropertyAnalysis.objects.filter(status='failed').count()
        
        # Cache stats
        cache_stats = get_performance_stats()
        
        logger.info(f"SYSTEM HEALTH: {total_properties} properties, {completed_analyses} completed, {failed_analyses} failed")
        logger.info(f"CACHE STATS: {cache_stats.get('cache_stats', {})}")
        
        # Performance warnings
        if failed_analyses > completed_analyses * 0.1:  # More than 10% failure rate
            logger.warning(f"HIGH FAILURE RATE: {failed_analyses}/{completed_analyses} analyses failed")
        
        if total_properties > 10000:
            logger.info(f"LARGE DATABASE: {total_properties} properties - consider archiving old data")
            
    except Exception as e:
        logger.error(f"Error logging system health: {e}")

# Existing utility functions
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
