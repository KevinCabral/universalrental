from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key.
    Usage: {{ my_dict|get_item:my_key }}
    """
    if dictionary is None:
        return None
    
    # Convert key to int if it's a string representation of a number
    try:
        if isinstance(key, str) and key.isdigit():
            key = int(key)
        elif isinstance(key, int):
            key = int(key)
    except (ValueError, TypeError):
        pass
    
    return dictionary.get(key, 0)
