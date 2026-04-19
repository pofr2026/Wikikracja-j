# Third party imports
from django import template
from django.db.models import Count

# First party imports
from chat.models import Room

register = template.Library()


@register.filter('name_for')
def name_for(room, user):
    """Returns name of room given user will see"""
    return room.displayed_name(user)


def _is_seen(room, user):
    """Core logic: returns True if room has been seen by user."""
    # Annotated queryset (fast path)
    if hasattr(room, 'is_seen') and hasattr(room, 'messages_count'):
        return room.is_seen or room.messages_count == 0
    # Prefetched seen_by (e.g. via select_related + Prefetch on task.chat_room)
    if hasattr(room, '_prefetched_objects_cache') and 'seen_by' in room._prefetched_objects_cache:
        return any(u.id == user.id for u in room.seen_by.all())
    # Fallback: direct query
    return room.messages.all().count() == 0 or room.seen_by.filter(id=user.id).exists()


@register.filter('is_seen_by')
def is_seen_by(room, user):
    """Returns 'true'/'false' string for JS data-seen attribute."""
    return "true" if _is_seen(room, user) else "false"


@register.filter('seen_by')
def seen_by(room, user):
    """Returns CSS class string: '' if seen, 'room-not-seen' if unseen."""
    return "" if _is_seen(room, user) else "room-not-seen"


@register.filter('is_muted_by')
def is_muted_by(room, user):
    """Returns True if the room is muted by the user"""
    # Use prefetched data if available
    if hasattr(room, '_prefetched_objects_cache') and 'muted_by' in room._prefetched_objects_cache:
        return any(u.id == user.id for u in room.muted_by.all())
    return room.muted_by.filter(id=user.id).exists()


@register.filter('not_participated')
def not_participated(room, participated_room_ids):
    """Returns True if user has not participated in this room (and participated_only mode is on)."""
    return room.id not in participated_room_ids


@register.filter("has_messages")
def has_messages(user):
    rooms_with_new_messages = (Room.objects.filter(allowed=user.id, archived=False).exclude(seen_by=user.id).annotate(messages_count=Count('messages')).filter(messages_count__gt=0))
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
