from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()


@register.filter
def getattribute(obj, attr):
    """
    Gets an attribute of an object dynamically from a string name.
    
    Usage: {{ profile|getattribute:field_name }}
    """
    return getattr(obj, attr, None)


@register.inclusion_tag('obywatele/includes/notification_row.html')
def notification_row(notification_type, title, description, is_enabled):
    """
    Renders a notification settings row.
    
    Args:
        notification_type: Type identifier (e.g., 'obywatele', 'glosowania', 'chat')
        title: Display title for the notification type
        description: Description text for the notification
        is_enabled: Boolean indicating if notification is currently enabled
    """
    return {
        'notification_type': notification_type,
        'title': title,
        'description': description,
        'is_enabled': is_enabled,
    }
