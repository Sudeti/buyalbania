from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Template filter to access dictionary values by key"""
    return dictionary.get(key, None)

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def div(value, arg):
    """Divide value by arg"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0