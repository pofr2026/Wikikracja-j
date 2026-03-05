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
    return "" if (room.seen_by.filter(id=user.id) or room.messages.all().count() == 0) else "room-not-seen"


@register.filter("has_messages")
def has_messages(user):
    rooms_with_new_messages = (
            Room.objects.filter(allowed=user.id)
            .exclude(seen_by=user.id)
            .annotate(messages_count=Count('messages'))
            .filter(messages_count__gt=0)
        )
    return "chat-has-messages" if rooms_with_new_messages.count() > 0 else ""
