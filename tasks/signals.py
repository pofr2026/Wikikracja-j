from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
import logging

from .models import Task

log = logging.getLogger(__name__)


@receiver(post_save, sender=Task)
def create_task_chat_room(sender, instance, created, **kwargs):
    """
    Automatically create a public chat room for each new task
    """
    if created:
        from chat.models import Room, Message
        
        room_title = instance.get_chat_room_title()
        
        # Check if room already exists
        if Room.objects.filter(title=room_title).exists():
            log.info(f"Chat room '{room_title}' already exists")
            return
        
        # Create new public room
        room = Room.objects.create(
            title=room_title,
            public=True,
            archived=False,
            last_activity=timezone.now()
        )
        
        # Allow all active users access to the room
        active_users = User.objects.filter(is_active=True)
        room.allowed.set(active_users)
        
        log.info(f"Created chat room '{room_title}' for task #{instance.id}")
        
        # Send initial message with link back to the task
        from django.contrib.sites.models import Site
        try:
            current_site = Site.objects.get_current()
            domain = current_site.domain
        except:
            # Fallback to settings if Site framework is not configured
            from django.conf import settings
            domain = getattr(settings, 'DOMAIN', 'localhost:8000')
        
        task_path = reverse('tasks:detail', kwargs={'pk': instance.pk})
        task_url = f"https://{domain}{task_path}"
        message_text = f'Discussion room for task: {task_url}'
        
        Message.objects.create(
            sender=instance.created_by,
            text=message_text,
            room=room,
            anonymous=False
        )
        
        log.info(f"Sent initial message to chat room '{room_title}'")
