from django import template

register = template.Library()


@register.filter
def content_type_color(content_type):
    """Return Bootstrap color class for content type"""
    color_map = {
        'post': 'primary',
        'task': 'success',
        'book': 'info',
        'event': 'warning',
        'message': 'danger',
        'decision': 'secondary',
        'membership': 'dark',
        'transaction': 'warning',
    }
    return color_map.get(content_type, 'secondary')
