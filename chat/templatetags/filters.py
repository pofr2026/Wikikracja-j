from django import template

from chat.models import Room
from django.db.models import Count

register = template.Library()


@register.filter('name_for')
def name_for(room, user):
    """Returns name of room given user will see"""
    return room.displayed_name(user)


@register.filter('seen_by')
def seen_by(room, user):
    # Use pre-computed annotations from the view if available
    if hasattr(room, 'is_seen') and hasattr(room, 'messages_count'):
        return "" if (room.is_seen or room.messages_count == 0) else "room-not-seen"
    # Fallback to original logic if annotations not available
    return "" if (room.messages.all().count() == 0 or room.seen_by.filter(id=user.id).exists()) else "room-not-seen"


@register.filter("has_messages")
def has_messages(user):
    rooms_with_new_messages = (
            Room.objects.filter(allowed=user.id, archived=False)
            .exclude(seen_by=user.id)
            .annotate(messages_count=Count('messages'))
            .filter(messages_count__gt=0)
        )
    count = rooms_with_new_messages.count()
    return "chat-has-messages" if count > 0 else ""
    
    # from django.core.cache import cache
    # rooms_with_new_messages = cache.get('has_messages')
    
    # if not rooms_with_new_messages:
    #     rooms_with_new_messages = (
    #             Room.objects.filter(allowed=user.id, archived=False)
    #             .exclude(seen_by=user.id)
    #             .annotate(messages_count=Count('messages'))
    #             .filter(messages_count__gt=0)
    #         )
    #     cache.set("has_messages", rooms_with_new_messages, timeout=60)
    # count = rooms_with_new_messages.count()
    # return "chat-has-messages" if count > 0 else ""