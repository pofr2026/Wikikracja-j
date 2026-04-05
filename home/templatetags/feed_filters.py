from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def content_type_color(content_type):
    """Return Bootstrap color class for content type"""
    color_map = {
        'post': 'primary',
        'task': 'success',
        'book': 'secondary',
        'event': 'primary',
        'message': 'primary',
        'decision': 'danger',
        'citizen': 'danger',
        'membership': 'secondary',
        'transaction': 'primary',
    }
    return color_map.get(content_type, 'secondary')


@register.filter
def content_type_label(content_type):
    """Return translated label for content type"""
    label_map = {
        'post': _('Post'),
        'task': _('Task'),
        'book': _('Book'),
        'event': _('Event'),
        'message': _('Message'),
        'decision': _('Decision'),
        'citizen': _('Citizen'),
        'membership': _('Membership'),
        'transaction': _('Transaction'),
    }
    return label_map.get(content_type, content_type.title())
