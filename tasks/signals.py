# Standard library imports
import logging

# Third party imports
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

# First party imports
from chat.models import Message, Room
from zzz.utils import get_site_domain

# Local folder imports
from .models import Task

log = logging.getLogger(__name__)


@receiver(post_save, sender=Task)
def create_task_chat_room(sender, instance, created, **kwargs):
    """
    Automatically create a public chat room for each new task
    """
    if created:

        def _create_room():
            room_title = instance.get_chat_room_title()

            # Check if room already exists (e.g. from a previous attempt)
            existing = Room.objects.filter(title=room_title).first()
            if existing:
                log.info(f"Chat room '{room_title}' already exists, linking to task #{instance.id}")
                Task.objects.filter(pk=instance.pk).update(chat_room=existing)
                return

            # Create new public room
            room = Room.objects.create(title=room_title, public=True, archived=False, protected=True, last_activity=timezone.now())

            # Allow all active users access to the room
            active_users = User.objects.filter(is_active=True)
            room.allowed.set(active_users)

            # Link room to task via FK
            Task.objects.filter(pk=instance.pk).update(chat_room=room)

            log.info(f"Created chat room '{room_title}' for task #{instance.id}")

            # Send initial message with link back to the task
            domain = get_site_domain()
            task_path = reverse('tasks:detail', kwargs={
                'pk': instance.pk
            })
            task_url = f"https://{domain}{task_path}"
            message_text = _('Discussion room for task: %(task_url)s') % {
                'task_url': task_url
            }

            Message.objects.create(sender=instance.created_by, text=message_text, room=room, anonymous=False)

            log.info(f"Sent initial message to chat room '{room_title}'")

        transaction.on_commit(_create_room)


@receiver(pre_delete, sender=Task)
def delete_task_chat_room(sender, instance, **kwargs):
    """
    Automatically delete the associated chat room when a task is deleted
    """
    room = instance.chat_room
    if room:
        room.delete()
        log.info(f"Deleted chat room '{room}' for task #{instance.id}")
    else:
        log.info(f"No chat room linked to task #{instance.id}, nothing to delete")
