from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces"""
    if value:
        return value.replace('_', ' ')
    return value
